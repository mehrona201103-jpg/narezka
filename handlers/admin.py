from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from database import (
    get_all_users_count, get_vip_users_count, get_movies_count,
    get_pending_payments, process_payment, get_partners,
    add_movie, delete_movie, get_all_movies, set_vip_price, get_vip_price,
    set_about_text, get_about_text, get_user
)
from utils.keyboards import admin_menu_kb, payment_actions_kb, confirm_delete_kb, back_to_menu_kb

router = Router()


class AdminStates(StatesGroup):
    add_movie_id = State()
    add_movie_title = State()
    add_movie_genre = State()
    add_movie_link = State()
    add_movie_cover = State()
    delete_movie_id = State()
    change_price = State()
    edit_about = State()


def admin_only(func):
    async def wrapper(event, *args, **kwargs):
        user_id = event.from_user.id if hasattr(event, "from_user") else None
        if user_id != ADMIN_ID:
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ только админу", show_alert=True)
            else:
                await event.answer("⛔ Доступ только админу")
            return
        return await func(event, *args, **kwargs)
    return wrapper


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён")
        return
    await message.answer(
        "🛠 <b>Админ-панель</b>\n\nВыбери действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return
    users = await get_all_users_count()
    vips = await get_vip_users_count()
    movies = await get_movies_count()
    pending = len(await get_pending_payments())
    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: <b>{users}</b>\n"
        f"⭐ VIP-пользователей: <b>{vips}</b>\n"
        f"🎬 Фильмов в базе: <b>{movies}</b>\n"
        f"💳 Ожидающих заявок: <b>{pending}</b>"
    )
    await callback.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return
    users = await get_all_users_count()
    vips = await get_vip_users_count()
    await callback.message.edit_text(
        f"👥 <b>Пользователи</b>\n\n"
        f"Всего: <b>{users}</b>\n"
        f"VIP: <b>{vips}</b>\n\n"
        f"Подробный список можно смотреть в базе данных.",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:partners")
async def admin_partners(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return
    partners = await get_partners()
    if not partners:
        text = "🤝 Партнёров пока нет."
    else:
        lines = ["🤝 <b>Партнёры</b>\n"]
        for p in partners[:30]:
            lines.append(
                f"• @{p.username or p.user_id} | {p.status}\n"
                f"  Ссылки: {p.social_links[:80]}...\n"
                f"  Просмотры: {p.total_views} | Заработано: {p.total_earned} ⭐"
            )
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:payments")
async def admin_payments(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return
    pending = await get_pending_payments()
    if not pending:
        await callback.message.edit_text(
            "💳 Нет ожидающих заявок.",
            reply_markup=admin_menu_kb()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"💳 <b>Заявки на оплату</b> ({len(pending)} шт.)\n\nВыбери заявку:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )
    for req in pending[:10]:
        await callback.message.answer_photo(
            photo=req.screenshot_file_id,
            caption=(
                f"Заявка <code>#{req.id}</code>\n"
                f"User: @{req.username or 'нет'} (<code>{req.user_id}</code>)\n"
                f"Сумма: <b>{req.amount} ⭐</b>\n"
                f"Дата: {req.created_at.strftime('%d.%m.%Y %H:%M')}"
            ),
            reply_markup=payment_actions_kb(req.id),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:pay_approve:"))
async def admin_pay_approve(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return
    req_id = int(callback.data.split(":")[2])
    req = await process_payment(req_id, approve=True)
    if not req:
        await callback.answer("Заявка уже обработана или не найдена", show_alert=True)
        return
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>ОДОБРЕНО</b>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            chat_id=req.user_id,
            text=f"🎉 Твоя заявка #{req.id} одобрена!\n⭐ VIP активирован на 30 дней."
        )
    except Exception:
        pass
    await callback.answer("✅ Одобрено")


@router.callback_query(F.data.startswith("admin:pay_reject:"))
async def admin_pay_reject(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return
    req_id = int(callback.data.split(":")[2])
    req = await process_payment(req_id, approve=False)
    if not req:
        await callback.answer("Заявка уже обработана", show_alert=True)
        return
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            chat_id=req.user_id,
            text=f"❌ Заявка #{req.id} отклонена.\nПроверь скриншот и попробуй снова."
        )
    except Exception:
        pass
    await callback.answer("❌ Отклонено")


# ==================== ДОБАВИТЬ КИНО ====================
@router.callback_query(F.data == "admin:add_movie")
async def admin_add_movie(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return
    await state.set_state(AdminStates.add_movie_id)
    await callback.message.edit_text(
        "➕ <b>Добавление кино</b>\n\nШаг 1/5: Введи уникальный <b>ID</b> фильма (например movie_001):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.add_movie_id)
async def add_movie_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(movie_id=message.text.strip())
    await state.set_state(AdminStates.add_movie_title)
    await message.answer("Шаг 2/5: Введи <b>название</b> фильма:", parse_mode="HTML")


@router.message(AdminStates.add_movie_title)
async def add_movie_title(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminStates.add_movie_genre)
    await message.answer("Шаг 3/5: Введи <b>жанр</b> (или «—»):", parse_mode="HTML")


@router.message(AdminStates.add_movie_genre)
async def add_movie_genre(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(genre=message.text.strip())
    await state.set_state(AdminStates.add_movie_link)
    await message.answer("Шаг 4/5: Введи <b>YouTube-ссылку</b> на публикацию:", parse_mode="HTML")


@router.message(AdminStates.add_movie_link)
async def add_movie_link(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(youtube_link=message.text.strip())
    await state.set_state(AdminStates.add_movie_cover)
    await message.answer(
        "Шаг 5/5: Пришли <b>обложку</b> (фото) или напиши «пропустить»:",
        parse_mode="HTML"
    )


@router.message(AdminStates.add_movie_cover, F.photo)
async def add_movie_cover_photo(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    cover_id = message.photo[-1].file_id
    movie = await add_movie(
        movie_id=data["movie_id"],
        title=data["title"],
        genre=data["genre"],
        youtube_link=data["youtube_link"],
        cover_file_id=cover_id
    )
    await state.clear()
    await message.answer(
        f"✅ Кино добавлено!\n"
        f"ID: <code>{movie.movie_id}</code>\n"
        f"Название: {movie.title}",
        parse_mode="HTML",
        reply_markup=admin_menu_kb()
    )


@router.message(AdminStates.add_movie_cover)
async def add_movie_cover_skip(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    movie = await add_movie(
        movie_id=data["movie_id"],
        title=data["title"],
        genre=data["genre"],
        youtube_link=data["youtube_link"],
        cover_file_id=None
    )
    await state.clear()
    await message.answer(
        f"✅ Кино добавлено (без обложки)!\n"
        f"ID: <code>{movie.movie_id}</code>\n"
        f"Название: {movie.title}",
        parse_mode="HTML",
        reply_markup=admin_menu_kb()
    )


# ==================== УДАЛИТЬ КИНО ====================
@router.callback_query(F.data == "admin:delete_movie")
async def admin_delete_movie(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return
    movies = await get_all_movies()
    if not movies:
        await callback.message.edit_text("🗑 В базе нет фильмов.", reply_markup=admin_menu_kb())
        await callback.answer()
        return
    lines = ["🗑 <b>Удаление кино</b>\n\nСписок (ID — название):\n"]
    for m in movies[:40]:
        lines.append(f"• <code>{m.movie_id}</code> — {m.title}")
    lines.append("\nВведи ID фильма для удаления:")
    await state.set_state(AdminStates.delete_movie_id)
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.message(AdminStates.delete_movie_id)
async def process_delete_movie(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    movie_id = message.text.strip()
    ok = await delete_movie(movie_id)
    await state.clear()
    if ok:
        await message.answer(f"✅ Фильм <code>{movie_id}</code> удалён.", parse_mode="HTML", reply_markup=admin_menu_kb())
    else:
        await message.answer(f"❌ Фильм с ID <code>{movie_id}</code> не найден.", parse_mode="HTML", reply_markup=admin_menu_kb())


# ==================== ЦЕНА VIP ====================
@router.callback_query(F.data == "admin:change_price")
async def admin_change_price(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return
    current = await get_vip_price()
    await state.set_state(AdminStates.change_price)
    await callback.message.edit_text(
        f"💰 Текущая цена VIP: <b>{current} ⭐</b>\n\nВведи новую цену (число):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.change_price)
async def process_change_price(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        price = int(message.text.strip())
        if price < 1:
            raise ValueError
    except ValueError:
        await message.answer("Введи целое число больше 0.")
        return
    await set_vip_price(price)
    await state.clear()
    await message.answer(f"✅ Новая цена VIP: <b>{price} ⭐</b>", parse_mode="HTML", reply_markup=admin_menu_kb())


# ==================== О БОТЕ ====================
@router.callback_query(F.data == "admin:edit_about")
async def admin_edit_about(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔", show_alert=True)
        return
    current = await get_about_text()
    await state.set_state(AdminStates.edit_about)
    await callback.message.edit_text(
        f"📝 Текущий текст «О боте»:\n\n{current}\n\n"
        f"Пришли новый текст:"
    )
    await callback.answer()


@router.message(AdminStates.edit_about)
async def process_edit_about(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await set_about_text(message.text)
    await state.clear()
    await message.answer("✅ Текст «О боте» обновлён.", reply_markup=admin_menu_kb())
