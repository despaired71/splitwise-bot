"""FSM states for multi-step forms."""

from aiogram.fsm.state import State, StatesGroup


class EventForm(StatesGroup):
    """States for creating/editing an event."""
    name = State()
    description = State()
    confirm = State()


class ParticipantForm(StatesGroup):
    """States for adding a participant."""
    select_event = State()
    participant_type = State()  # telegram user, external user, by name
    user_input = State()  # username or name
    confirm = State()


class FamilyForm(StatesGroup):
    """States for creating a family in event."""
    select_event = State()
    use_template = State()  # Use existing template or create new
    select_template = State()  # If using template
    family_name = State()  # If creating new
    select_members = State()
    select_head = State()
    save_as_template = State()  # Ask if want to save as template
    confirm = State()


class GlobalFamilyForm(StatesGroup):
    """States for creating a global family template."""
    family_name = State()
    add_member_type = State()  # telegram user or by name
    member_input = State()  # username or name
    add_more = State()  # Add more members?
    select_head = State()
    confirm = State()


class ExpenseForm(StatesGroup):
    """States for adding an expense."""
    select_event = State()
    amount = State()
    description = State()
    category = State()  # Optional
    split_type = State()  # equal, custom, specific
    select_participants = State()  # If split_type is specific
    custom_amounts = State()  # If split_type is custom
    confirm = State()


class EditExpenseForm(StatesGroup):
    """States for editing an expense."""
    select_expense = State()
    select_field = State()  # What to edit: amount, description, split
    new_value = State()
    confirm = State()


class CalculateForm(StatesGroup):
    """States for calculating debts."""
    select_event = State()
    confirm_send = State()  # Send notifications?