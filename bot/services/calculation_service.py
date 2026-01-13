"""Service for calculating debts and settlements."""

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import (
    Event, Participant, Expense, ExpenseSplit,
    Family, FamilyMember, DebtSettlement
)


class CalculationService:
    """Service for debt calculations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def calculate_debts(
            self,
            event_id: int
    ) -> Dict[int, Dict[str, any]]:
        """
        Calculate who owes whom and by how much.

        This implements the debt minimization algorithm:
        1. Calculate net balance for each participant (considering families)
        2. Match debtors with creditors to minimize transactions

        Args:
            event_id: Event ID

        Returns:
            Dictionary with participant_id as key and dict containing:
            - name: participant name
            - balance: net balance (positive = owed, negative = owes)
            - debts: list of {to_id, to_name, amount} they need to pay
            - credits: list of {from_id, from_name, amount} they will receive
        """
        # Get all expenses and their splits
        expenses = await self._get_event_expenses(event_id)

        # Get all participants and families
        participants = await self._get_event_participants(event_id)
        families = await self._get_event_families(event_id)

        # Build family membership map
        family_map = await self._build_family_map(event_id)

        # Calculate balances
        balances = await self._calculate_balances(
            expenses, participants, families, family_map
        )

        # Minimize transactions
        settlements = self._minimize_transactions(balances)

        # Build result dictionary
        result = {}
        for participant_id, participant_name in participants.items():
            balance = balances.get(participant_id, Decimal(0))

            debts = []
            credits = []

            for debtor_id, creditor_id, amount in settlements:
                if debtor_id == participant_id:
                    debts.append({
                        "to_id": creditor_id,
                        "to_name": participants[creditor_id],
                        "amount": amount
                    })
                elif creditor_id == participant_id:
                    credits.append({
                        "from_id": debtor_id,
                        "from_name": participants[debtor_id],
                        "amount": amount
                    })

            result[participant_id] = {
                "name": participant_name,
                "balance": balance,
                "debts": debts,
                "credits": credits
            }

        return result

    async def save_settlements(
            self,
            event_id: int,
            settlements: List[Tuple[int, int, Decimal]]
    ):
        """
        Save calculated settlements to database.

        Args:
            event_id: Event ID
            settlements: List of (debtor_id, creditor_id, amount) tuples
        """
        # Clear existing settlements
        await self.session.execute(
            select(DebtSettlement)
            .where(DebtSettlement.event_id == event_id)
        )

        # Create new settlements
        for debtor_id, creditor_id, amount in settlements:
            settlement = DebtSettlement(
                event_id=event_id,
                debtor_id=debtor_id,
                creditor_id=creditor_id,
                amount=amount,
                settled=False
            )
            self.session.add(settlement)

    async def _get_event_expenses(self, event_id: int) -> List[Expense]:
        """Get all non-deleted expenses for an event."""
        result = await self.session.execute(
            select(Expense)
            .where(and_(
                Expense.event_id == event_id,
                Expense.is_deleted == False
            ))
            .options(selectinload(Expense.splits))
        )
        return list(result.scalars().all())

    async def _get_event_participants(
            self,
            event_id: int
    ) -> Dict[int, str]:
        """Get all active participants as {id: name} dict."""
        result = await self.session.execute(
            select(Participant)
            .where(and_(
                Participant.event_id == event_id,
                Participant.is_active == True
            ))
        )
        participants = result.scalars().all()
        return {p.id: p.display_name for p in participants}

    async def _get_event_families(self, event_id: int) -> Dict[int, Family]:
        """Get all families as {id: Family} dict."""
        result = await self.session.execute(
            select(Family)
            .where(Family.event_id == event_id)
            .options(selectinload(Family.members))
        )
        families = result.scalars().all()
        return {f.id: f for f in families}

    async def _build_family_map(
            self,
            event_id: int
    ) -> Dict[int, Tuple[int, int]]:
        """
        Build map of participant_id -> (family_id, family_head_id).

        Returns:
            Dict mapping participant IDs to their family and family head
        """
        result = await self.session.execute(
            select(FamilyMember, Family)
            .join(Family, FamilyMember.family_id == Family.id)
            .where(Family.event_id == event_id)
        )

        family_map = {}
        for member, family in result.all():
            family_map[member.participant_id] = (family.id, family.family_head_id)

        return family_map

    async def _calculate_balances(
            self,
            expenses: List[Expense],
            participants: Dict[int, str],
            families: Dict[int, Family],
            family_map: Dict[int, Tuple[int, int]]
    ) -> Dict[int, Decimal]:
        """
        Calculate net balance for each participant.

        Balance = Total paid - Total owed
        Positive balance = person is owed money
        Negative balance = person owes money
        """
        balances = defaultdict(lambda: Decimal(0))

        for expense in expenses:
            # Add amount paid to payer's balance
            payer_id = expense.payer_id

            # If payer is in a family, credit goes to family head
            if payer_id in family_map:
                _, family_head_id = family_map[payer_id]
                if family_head_id:
                    payer_id = family_head_id

            balances[payer_id] += expense.amount

            # Distribute expense among splits
            if expense.split_type == "equal":
                # Equal split among all specified people/families
                share_amount = expense.amount / len(expense.splits)

                for split in expense.splits:
                    if split.participant_id:
                        # Individual participant
                        participant_id = split.participant_id

                        # If in family, debit from family head
                        if participant_id in family_map:
                            _, family_head_id = family_map[participant_id]
                            if family_head_id:
                                participant_id = family_head_id

                        balances[participant_id] -= share_amount

                    elif split.family_id:
                        # Entire family
                        family = families[split.family_id]
                        family_size = len(family.members)
                        family_share = share_amount * family_size

                        # Debit from family head
                        if family.family_head_id:
                            balances[family.family_head_id] -= family_share

            elif expense.split_type == "custom":
                # Custom amounts or percentages
                for split in expense.splits:
                    amount = split.share_amount or (
                            expense.amount * split.share_percentage / 100
                    )

                    if split.participant_id:
                        participant_id = split.participant_id

                        if participant_id in family_map:
                            _, family_head_id = family_map[participant_id]
                            if family_head_id:
                                participant_id = family_head_id

                        balances[participant_id] -= amount

                    elif split.family_id:
                        family = families[split.family_id]
                        if family.family_head_id:
                            balances[family.family_head_id] -= amount

            elif expense.split_type == "specific":
                # Specific amounts for specific people
                for split in expense.splits:
                    amount = split.share_amount

                    if split.participant_id:
                        participant_id = split.participant_id

                        if participant_id in family_map:
                            _, family_head_id = family_map[participant_id]
                            if family_head_id:
                                participant_id = family_head_id

                        balances[participant_id] -= amount

                    elif split.family_id:
                        family = families[split.family_id]
                        if family.family_head_id:
                            balances[family.family_head_id] -= amount

        return dict(balances)

    def _minimize_transactions(
            self,
            balances: Dict[int, Decimal]
    ) -> List[Tuple[int, int, Decimal]]:
        """
        Minimize number of transactions using greedy algorithm.

        Algorithm:
        1. Separate into debtors (negative balance) and creditors (positive)
        2. Match largest debtor with largest creditor
        3. Settle as much as possible
        4. Repeat until all settled

        Args:
            balances: Dict of participant_id -> balance

        Returns:
            List of (debtor_id, creditor_id, amount) tuples
        """
        settlements = []

        # Separate debtors and creditors
        debtors = [(pid, -bal) for pid, bal in balances.items() if bal < 0]
        creditors = [(pid, bal) for pid, bal in balances.items() if bal > 0]

        # Sort by amount (descending)
        debtors.sort(key=lambda x: x[1], reverse=True)
        creditors.sort(key=lambda x: x[1], reverse=True)

        i, j = 0, 0

        while i < len(debtors) and j < len(creditors):
            debtor_id, debt = debtors[i]
            creditor_id, credit = creditors[j]

            # Settle the minimum of debt and credit
            amount = min(debt, credit)

            # Round to 2 decimal places
            amount = round(amount, 2)

            if amount > Decimal("0.01"):  # Only record if > 1 cent
                settlements.append((debtor_id, creditor_id, amount))

            # Update balances
            debtors[i] = (debtor_id, debt - amount)
            creditors[j] = (creditor_id, credit - amount)

            # Move to next if settled
            if debtors[i][1] < Decimal("0.01"):
                i += 1
            if creditors[j][1] < Decimal("0.01"):
                j += 1

        return settlements