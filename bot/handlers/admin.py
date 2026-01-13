"""Admin handlers for system management."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.admin_service import AdminService
from bot.services.event_service import EventService
from bot.keyboards.inline import get_admin_menu_keyboard, get_events_keyboard, get_admin_back_keyboard

router = Router()


def admin_only(handler):
    """Decorator to check if user is admin."""
    async def wrapper(message: Message, is_admin: bool, *args, **kwargs):
        if not is_admin:
            await message.answer("❌ Эта команда доступна только администраторам")
            return
        return await handler(message, *args, **kwargs)
    return wrapper


@router.callback_query(F.data == "admin:menu")
async def callback_admin_back_to_menu(callback: CallbackQuery, is_admin: bool):
    """Handle back to menu button click."""
    if not is_admin:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    await callback.message.edit_text(
        "👨‍💼 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.message(Command("admin"))
async def cmd_admin_menu(message: Message, is_admin: bool):
    """Show admin menu."""
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return

    await message.answer(
        "👨‍💼 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_menu_keyboard()
    )


# Callback handlers for admin menu buttons
@router.callback_query(F.data == "admin:stats")
async def callback_admin_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    is_admin: bool
):
    """Handle stats button click."""
    if not is_admin:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    admin_service = AdminService(session)
    stats = await admin_service.get_system_stats()

    msg = "📊 <b>Статистика системы</b>\n\n"
    msg += f"📋 <b>Мероприятия:</b>\n"
    msg += f"  • Всего: {stats['total_events']}\n"
    msg += f"  • Активных: {stats['active_events']}\n\n"

    msg += f"👥 <b>Пользователи:</b>\n"
    msg += f"  • Всего участников: {stats['total_participants']}\n"
    msg += f"  • Уникальных: {stats['unique_users']}\n\n"

    msg += f"💰 <b>Расходы:</b>\n"
    msg += f"  • Всего записей: {stats['total_expenses']}\n"
    msg += f"  • Сумма: {stats['total_amount']:.2f} ₽\n\n"

    msg += f"👨‍👩‍👧‍👦 <b>Семьи:</b>\n"
    msg += f"  • Всего: {stats['total_families']}\n"
    msg += f"  • Шаблонов: {stats['global_families']}\n"

    await callback.message.edit_text(msg, reply_markup=get_admin_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:events")
async def callback_admin_events(
    callback: CallbackQuery,
    session: AsyncSession,
    is_admin: bool
):
    """Handle events button click."""
    if not is_admin:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    admin_service = AdminService(session)
    events = await admin_service.get_all_events(limit=20)

    if not events:
        await callback.message.edit_text(
            "📋 В системе пока нет мероприятий",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
        return

    events_data = [(e.id, f"{e.name} ({e.status})") for e in events]
    keyboard = get_events_keyboard(events_data, action="admin_view_event")

    await callback.message.edit_text(
        f"📋 <b>Все мероприятия ({len(events)}):</b>\n\n"
        "Выберите для просмотра:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "admin:top")
async def callback_admin_top(
    callback: CallbackQuery,
    session: AsyncSession,
    is_admin: bool
):
    """Handle top spenders button click."""
    if not is_admin:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    admin_service = AdminService(session)
    spenders = await admin_service.get_top_spenders(limit=10)

    if not spenders:
        await callback.message.edit_text(
            "📊 Нет данных о расходах",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
        return

    msg = "🏆 <b>Топ-10 по расходам:</b>\n\n"

    for i, spender in enumerate(spenders, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        msg += f"{emoji} <b>{spender['name']}</b>\n"
        msg += f"   💰 {spender['total_amount']:.2f} ₽ ({spender['expense_count']} расходов)\n"
        if spender['user_id']:
            msg += f"   ID: {spender['user_id']}\n"
        msg += "\n"

    await callback.message.edit_text(msg, reply_markup=get_admin_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:activity")
async def callback_admin_activity(
    callback: CallbackQuery,
    session: AsyncSession,
    is_admin: bool
):
    """Handle activity button click."""
    if not is_admin:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    admin_service = AdminService(session)
    logs = await admin_service.get_recent_activity(limit=15)

    if not logs:
        await callback.message.edit_text(
            "📝 Нет записей активности",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
        return

    msg = "📝 <b>Последняя активность:</b>\n\n"

    action_emoji = {
        "create": "➕",
        "update": "✏️",
        "delete": "🗑"
    }

    entity_emoji = {
        "event": "📋",
        "participant": "👤",
        "family": "👨‍👩‍👧‍👦",
        "expense": "💰"
    }

    for log in logs:
        action = action_emoji.get(log.action, "•")
        entity = entity_emoji.get(log.entity_type, "📄")

        msg += f"{action} {entity} "
        msg += f"<b>{log.entity_type}</b> #{log.entity_id}\n"
        msg += f"   Пользователь: {log.user_id}\n"
        msg += f"   {log.created_at.strftime('%d.%m %H:%M')}\n\n"

    await callback.message.edit_text(msg, reply_markup=get_admin_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:help")
async def callback_admin_help(callback: CallbackQuery, is_admin: bool):
    """Handle help button click."""
    if not is_admin:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    msg = "👨‍💼 <b>Команды администратора:</b>\n\n"

    msg += "📊 <b>Статистика:</b>\n"
    msg += "/admin_stats - общая статистика системы\n"
    msg += "/admin_top - топ-10 по расходам\n"
    msg += "/admin_activity - последняя активность\n\n"

    msg += "📋 <b>Мероприятия:</b>\n"
    msg += "/admin_events - все мероприятия\n"
    msg += "/admin_delete_event &lt;id&gt; - удалить мероприятие\n\n"

    msg += "👤 <b>Пользователи:</b>\n"
    msg += "/admin_user &lt;user_id&gt; - активность пользователя\n\n"

    msg += "❓ /admin_help - эта справка\n"

    await callback.message.edit_text(msg, reply_markup=get_admin_menu_keyboard())
    await callback.answer()


@router.message(Command("admin_stats"))
async def cmd_admin_stats(
    message: Message,
    session: AsyncSession,
    is_admin: bool
):
    """Show system statistics."""
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return

    admin_service = AdminService(session)
    stats = await admin_service.get_system_stats()

    msg = "📊 <b>Статистика системы</b>\n\n"
    msg += f"📋 <b>Мероприятия:</b>\n"
    msg += f"  • Всего: {stats['total_events']}\n"
    msg += f"  • Активных: {stats['active_events']}\n\n"

    msg += f"👥 <b>Пользователи:</b>\n"
    msg += f"  • Всего участников: {stats['total_participants']}\n"
    msg += f"  • Уникальных: {stats['unique_users']}\n\n"

    msg += f"💰 <b>Расходы:</b>\n"
    msg += f"  • Всего записей: {stats['total_expenses']}\n"
    msg += f"  • Сумма: {stats['total_amount']:.2f} ₽\n\n"

    msg += f"👨‍👩‍👧‍👦 <b>Семьи:</b>\n"
    msg += f"  • Всего: {stats['total_families']}\n"
    msg += f"  • Шаблонов: {stats['global_families']}\n"

    await message.answer(msg, parse_mode="HTML")


@router.message(Command("admin_events"))
async def cmd_admin_events(
    message: Message,
    session: AsyncSession,
    is_admin: bool
):
    """Show all events in the system."""
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return

    admin_service = AdminService(session)
    events = await admin_service.get_all_events(limit=20)

    if not events:
        await message.answer("📋 В системе пока нет мероприятий")
        return

    events_data = [(e.id, f"{e.name} ({e.status})") for e in events]
    keyboard = get_events_keyboard(events_data, action="admin_view")

    await message.answer(
        f"📋 <b>Все мероприятия ({len(events)}):</b>\n\n"
        "Выберите для просмотра:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_view_event:"))
async def callback_admin_view_event(
    callback: CallbackQuery,
    session: AsyncSession,
    is_admin: bool
):
    """View detailed event information."""
    if not is_admin:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    event_id = int(callback.data.split(":")[1])

    admin_service = AdminService(session)
    details = await admin_service.get_event_details(event_id)

    if not details:
        await callback.answer("❌ Мероприятие не найдено", show_alert=True)
        return

    event = details["event"]

    msg = f"📋 <b>Мероприятие #{event.id}</b>\n\n"
    msg += f"<b>Название:</b> {event.name}\n"
    if event.description:
        msg += f"<b>Описание:</b> {event.description}\n"
    msg += f"<b>Создатель:</b> {event.creator_id}\n"
    msg += f"<b>Статус:</b> {event.status}\n"
    msg += f"<b>Создано:</b> {event.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    msg += f"📊 <b>Статистика:</b>\n"
    msg += f"  • Участников: {details['participants_count']}\n"
    msg += f"  • Семей: {details['families_count']}\n"
    msg += f"  • Расходов: {details['expenses_count']}\n"
    msg += f"  • Сумма: {details['total_amount']:.2f} ₽\n"

    if event.is_deleted:
        msg += f"\n⚠️ <b>Мероприятие удалено</b>"

    await callback.message.edit_text(msg, reply_markup=get_admin_back_keyboard())
    await callback.answer()


@router.message(Command("admin_user"))
async def cmd_admin_user(
    message: Message,
    session: AsyncSession,
    is_admin: bool
):
    """Show user activity. Usage: /admin_user <user_id>"""
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return

    # Parse user_id from command
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите ID пользователя\n\n"
            "Использование: /admin_user <user_id>"
        )
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя")
        return

    admin_service = AdminService(session)
    activity = await admin_service.get_user_activity(user_id)

    msg = f"👤 <b>Активность пользователя {user_id}</b>\n\n"
    msg += f"📋 Создано мероприятий: {activity['events_created']}\n"
    msg += f"👥 Участвовал в: {activity['events_participated']}\n"
    msg += f"💰 Добавил расходов: {activity['expenses_added']}\n"
    msg += f"💵 Всего потратил: {activity['total_paid']:.2f} ₽\n"

    await message.answer(msg, parse_mode="HTML")


@router.message(Command("admin_top"))
async def cmd_admin_top_spenders(
    message: Message,
    session: AsyncSession,
    is_admin: bool
):
    """Show top spenders."""
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return

    admin_service = AdminService(session)
    spenders = await admin_service.get_top_spenders(limit=10)

    if not spenders:
        await message.answer("📊 Нет данных о расходах")
        return

    msg = "🏆 <b>Топ-10 по расходам:</b>\n\n"

    for i, spender in enumerate(spenders, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        msg += f"{emoji} <b>{spender['name']}</b>\n"
        msg += f"   💰 {spender['total_amount']:.2f} ₽ ({spender['expense_count']} расходов)\n"
        if spender['user_id']:
            msg += f"   ID: {spender['user_id']}\n"
        msg += "\n"

    await message.answer(msg, parse_mode="HTML")


@router.message(Command("admin_activity"))
async def cmd_admin_recent_activity(
    message: Message,
    session: AsyncSession,
    is_admin: bool
):
    """Show recent system activity."""
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return

    admin_service = AdminService(session)
    logs = await admin_service.get_recent_activity(limit=15)

    if not logs:
        await message.answer("📝 Нет записей активности")
        return

    msg = "📝 <b>Последняя активность:</b>\n\n"

    action_emoji = {
        "create": "➕",
        "update": "✏️",
        "delete": "🗑"
    }

    entity_emoji = {
        "event": "📋",
        "participant": "👤",
        "family": "👨‍👩‍👧‍👦",
        "expense": "💰"
    }

    for log in logs:
        action = action_emoji.get(log.action, "•")
        entity = entity_emoji.get(log.entity_type, "📄")

        msg += f"{action} {entity} "
        msg += f"<b>{log.entity_type}</b> #{log.entity_id}\n"
        msg += f"   Пользователь: {log.user_id}\n"
        msg += f"   {log.created_at.strftime('%d.%m %H:%M')}\n\n"

    await message.answer(msg, parse_mode="HTML")


@router.message(Command("admin_delete_event"))
async def cmd_admin_delete_event(
    message: Message,
    session: AsyncSession,
    is_admin: bool
):
    """Permanently delete an event. Usage: /admin_delete_event <event_id>"""
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите ID мероприятия\n\n"
            "Использование: /admin_delete_event <event_id>"
        )
        return

    try:
        event_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Некорректный ID мероприятия")
        return

    admin_service = AdminService(session)
    success = await admin_service.delete_event_permanently(event_id)

    if success:
        await message.answer(
            f"✅ Мероприятие #{event_id} удалено безвозвратно"
        )
    else:
        await message.answer(f"❌ Мероприятие #{event_id} не найдено")


@router.message(Command("admin_help"))
async def cmd_admin_help(message: Message, is_admin: bool):
    """Show admin commands help."""
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return

    msg = "👨‍💼 <b>Команды администратора:</b>\n\n"

    msg += "📊 <b>Статистика:</b>\n"
    msg += "/admin_stats - общая статистика системы\n"
    msg += "/admin_top - топ-10 по расходам\n"
    msg += "/admin_activity - последняя активность\n\n"

    msg += "📋 <b>Мероприятия:</b>\n"
    msg += "/admin_events - все мероприятия\n"
    msg += "/admin_delete_event <id> - удалить мероприятие\n\n"

    msg += "👤 <b>Пользователи:</b>\n"
    msg += "/admin_user <user_id> - активность пользователя\n\n"

    msg += "❓ /admin_help - эта справка\n"

    await message.answer(msg, parse_mode="HTML")