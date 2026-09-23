from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👤 Профиль", callback_data="menu:profile"))
    builder.row(InlineKeyboardButton(text="⭐ VIP", callback_data="menu:vip"))
    builder.row(InlineKeyboardButton(text="🔍 Поиск Кино", callback_data="menu:search"))
    builder.row(InlineKeyboardButton(text="ℹ️ О боте", callback_data="menu:about"))
    builder.row(InlineKeyboardButton(text="🤝 Партнёрства", callback_data="menu:partner"))
    return builder.as_markup()


def profile_kb(has_referral: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="profile:referral"))
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu:main"))
    return builder.as_markup()


def vip_kb(price: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"💳 Оплатить {price} ⭐", callback_data=f"vip:pay:{price}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu:main"))
    return builder.as_markup()


def vip_pay_confirm_kb(price: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📤 Я отправил подарок и скрин", callback_data=f"vip:screenshot:{price}"))
    builder.row(InlineKeyboardButton(text="◀️ Отмена", callback_data="menu:vip"))
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu:main"))
    return builder.as_markup()


def search_result_kb(movie_id: str, is_vip: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_vip:
        builder.row(InlineKeyboardButton(text="⬇️ Скачать (VIP)", callback_data=f"movie:download:{movie_id}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu:main"))
    return builder.as_markup()


def partner_start_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Готов", callback_data="partner:ready"))
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu:main"))
    return builder.as_markup()


def partner_links_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Я разместил ссылки", callback_data="partner:links_done"))
    builder.row(InlineKeyboardButton(text="◀️ Отмена", callback_data="menu:main"))
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"))
    builder.row(InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users"))
    builder.row(InlineKeyboardButton(text="🤝 Партнёры", callback_data="admin:partners"))
    builder.row(InlineKeyboardButton(text="💳 Заявки на оплату", callback_data="admin:payments"))
    builder.row(InlineKeyboardButton(text="➕ Добавить кино", callback_data="admin:add_movie"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить кино", callback_data="admin:delete_movie"))
    builder.row(InlineKeyboardButton(text="💰 Изменить цену VIP", callback_data="admin:change_price"))
    builder.row(InlineKeyboardButton(text="📝 Изменить «О боте»", callback_data="admin:edit_about"))
    builder.row(InlineKeyboardButton(text="◀️ В меню бота", callback_data="menu:main"))
    return builder.as_markup()


def payment_actions_kb(req_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin:pay_approve:{req_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:pay_reject:{req_id}")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:payments"))
    return builder.as_markup()


def confirm_delete_kb(movie_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"admin:confirm_del:{movie_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="admin:delete_movie")
    )
    return builder.as_markup()


def subscribe_kb(channel_link: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Подписаться на канал", url=channel_link))
    builder.row(InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub"))
    return builder.as_markup()
