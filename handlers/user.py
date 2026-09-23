import os
import asyncio
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from config import CHANNEL_ID, CHANNEL_LINK, ADMIN_USERNAME, ADMIN_ID, MAX_DOWNLOAD_SIZE_GB
from database import (
    get_or_create_user, get_user, check_vip_status, get_vip_price,
    get_about_text, search_movies, get_movie_by_id, create_payment_request,
    add_partner, get_days_with_us, increment_watched
)
from utils.keyboards import (
    main_menu_kb, profile_kb, vip_kb, vip_pay_confirm_kb, back_to_menu_kb,
    search_result_kb, partner_start_kb, partner_links_kb, subscribe_kb
)

router = Router()


class SearchState(StatesGroup):
    waiting_query = State()


class VipScreenshotState(StatesGroup):
    waiting_screenshot = State()


class PartnerState(StatesGroup):
    waiting_links = State()


class DownloadState(StatesGroup):
    waiting_link = State()


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """Проверка подписки на канал"""
    if not CHANNEL_ID:
        return True  # Если канал не настроен — пропускаем
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    args = message.text.split(maxsplit=1)
    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1].replace("ref_", ""))
        except ValueError:
            pass

    user = await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        referred_by=referred_by
    )

    if not await is_subscribed(bot, message.from_user.id):
        await message.answer(
            "👋 Добро пожаловать в <b>Нарезки Кино</b>!\n\n"
            "Чтобы пользоваться ботом, обязательно подпишись на наш канал:",
            reply_markup=subscribe_kb(CHANNEL_LINK),
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"🎬 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "Выбери действие в меню ниже:",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery, bot: Bot):
    if await is_subscribed(bot, callback.from_user.id):
        await callback.message.edit_text(
            f"🎬 Отлично! Подписка подтверждена.\n\n"
            f"Привет, <b>{callback.from_user.first_name}</b>!\n"
            "Выбери действие в меню:",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ты ещё не подписан на канал!", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🎬 Главное меню\nВыбери действие:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


# ==================== ПРОФИЛЬ ====================
@router.callback_query(F.data == "menu:profile")
async def menu_profile(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка профиля", show_alert=True)
        return

    is_vip = await check_vip_status(callback.from_user.id)
    days = await get_days_with_us(user)
    vip_status = "✅ Активен" if is_vip else "❌ Нет"
    if is_vip and user.vip_until:
        vip_status += f" до {user.vip_until.strftime('%d.%m.%Y')}"

    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Юзер: @{user.username or 'нет'}\n"
        f"📛 Имя: {user.full_name or '—'}\n"
        f"🎬 Просмотрено кино: <b>{user.movies_watched}</b>\n"
        f"📅 С нами: <b>{days}</b> дн.\n"
        f"⭐ VIP: {vip_status}\n"
        f"💰 Реферальный заработок: <b>{user.referral_earnings}</b> ⭐\n"
        f"💎 Баланс: <b>{user.stars_balance}</b> ⭐"
    )
    await callback.message.edit_text(text, reply_markup=profile_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "profile:referral")
async def profile_referral(callback: CallbackQuery, bot: Bot):
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
    text = (
        f"🔗 <b>Твоя реферальная ссылка</b>\n\n"
        f"<code>{ref_link}</code>\n\n"
        f"Приглашай друзей! Ты получишь <b>15%</b> от каждой покупки VIP рефералом.\n"
        f"Нажми на ссылку, чтобы скопировать."
    )
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    await callback.answer()


# ==================== VIP ====================
@router.callback_query(F.data == "menu:vip")
async def menu_vip(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    price = await get_vip_price()
    is_vip = await check_vip_status(callback.from_user.id)
    status = "✅ У тебя уже есть активный VIP!" if is_vip else "❌ VIP не активен"

    text = (
        f"⭐ <b>VIP-подписка</b>\n\n"
        f"{status}\n\n"
        f"Тариф: <b>{price} Telegram Stars</b> / месяц\n\n"
        f"<b>Что даёт VIP:</b>\n"
        f"• Скачивание фильмов в 1080p (до 5 ГБ)\n"
        f"• Приоритетная поддержка\n"
        f"• Эксклюзивный доступ\n\n"
        f"<b>Как оплатить:</b>\n"
        f"1. Нажми «Оплатить»\n"
        f"2. Перейди в ЛС админу @{ADMIN_USERNAME}\n"
        f"3. Отправь подарок на сумму тарифа\n"
        f"4. Сделай скриншот и пришли его сюда\n"
        f"5. Дождись одобрения админом"
    )
    await callback.message.edit_text(text, reply_markup=vip_kb(price), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("vip:pay:"))
async def vip_pay(callback: CallbackQuery):
    price = int(callback.data.split(":")[2])
    text = (
        f"💳 <b>Оплата VIP — {price} ⭐</b>\n\n"
        f"1. Перейди к админу: @{ADMIN_USERNAME}\n"
        f"2. Отправь <b>подарок</b> (Telegram Gift) на сумму <b>{price} звёзд</b>\n"
        f"3. Сделай скриншот отправки\n"
        f"4. Вернись сюда и нажми кнопку ниже, затем пришли скрин"
    )
    await callback.message.edit_text(text, reply_markup=vip_pay_confirm_kb(price), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("vip:screenshot:"))
async def vip_wait_screenshot(callback: CallbackQuery, state: FSMContext):
    price = int(callback.data.split(":")[2])
    await state.set_state(VipScreenshotState.waiting_screenshot)
    await state.update_data(vip_price=price)
    await callback.message.edit_text(
        "📸 Пришли <b>скриншот</b> отправленного подарка (фото):\n\n"
        "После отправки заявка уйдёт админу на проверку.",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(VipScreenshotState.waiting_screenshot, F.photo)
async def vip_screenshot_received(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    price = data.get("vip_price", 150)
    file_id = message.photo[-1].file_id

    req = await create_payment_request(
        user_id=message.from_user.id,
        username=message.from_user.username,
        amount=price,
        screenshot_file_id=file_id
    )
    await state.clear()

    await message.answer(
        f"✅ Заявка #{req.id} отправлена!\n"
        f"Админ проверит скриншот и активирует VIP.\n"
        f"Обычно это занимает несколько минут.",
        reply_markup=main_menu_kb()
    )

    # Уведомление админу
    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=(
                f"💳 <b>Новая заявка на оплату VIP</b>\n\n"
                f"ID заявки: <code>{req.id}</code>\n"
                f"Пользователь: @{message.from_user.username or 'нет'} (<code>{message.from_user.id}</code>)\n"
                f"Сумма: <b>{price} ⭐</b>\n\n"
                f"Используй /admin → Заявки на оплату"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.message(VipScreenshotState.waiting_screenshot)
async def vip_screenshot_not_photo(message: Message):
    await message.answer("⚠️ Пришли именно <b>фото</b> (скриншот).", parse_mode="HTML")


# ==================== ПОИСК КИНО ====================
@router.callback_query(F.data == "menu:search")
async def menu_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_query)
    await callback.message.edit_text(
        "🔍 <b>Поиск Кино</b>\n\n"
        "Напиши название, жанр или ID фильма:",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SearchState.waiting_query)
async def process_search(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer("Введи запрос для поиска.")
        return

    movies = await search_movies(query)
    await state.clear()

    if not movies:
        await message.answer(
            f"❌ По запросу «{query}» ничего не найдено.\n"
            "Админ ещё не добавил такое кино.",
            reply_markup=main_menu_kb()
        )
        return

    is_vip = await check_vip_status(message.from_user.id)
    for movie in movies:
        caption = (
            f"🎬 <b>{movie.title}</b>\n"
            f"🆔 ID: <code>{movie.movie_id}</code>\n"
            f"🏷 Жанр: {movie.genre or '—'}\n\n"
            f"📺 Смотреть на YouTube:\n{movie.youtube_link}"
        )
        kb = search_result_kb(movie.movie_id, is_vip)
        if movie.cover_file_id:
            try:
                await message.answer_photo(
                    photo=movie.cover_file_id,
                    caption=caption,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            except Exception:
                await message.answer(caption, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer(caption, reply_markup=kb, parse_mode="HTML")

        # Учитываем просмотр
        await increment_watched(message.from_user.id, movie.id)


@router.callback_query(F.data.startswith("movie:download:"))
async def movie_download_start(callback: CallbackQuery, state: FSMContext):
    is_vip = await check_vip_status(callback.from_user.id)
    if not is_vip:
        await callback.answer("❌ Скачивание доступно только VIP!", show_alert=True)
        return

    movie_id = callback.data.split(":")[2]
    movie = await get_movie_by_id(movie_id)
    if not movie:
        await callback.answer("Фильм не найден", show_alert=True)
        return

    await state.set_state(DownloadState.waiting_link)
    await state.update_data(movie_db_id=movie.id, youtube_link=movie.youtube_link)
    await callback.message.answer(
        f"⬇️ <b>Скачивание VIP</b>\n\n"
        f"Фильм: <b>{movie.title}</b>\n\n"
        f"Отправь ссылку на это кино (или любую YouTube-ссылку),\n"
        f"и бот скачает его в 1080p (до {MAX_DOWNLOAD_SIZE_GB} ГБ).\n\n"
        f"Или просто отправь текущую ссылку:\n<code>{movie.youtube_link}</code>",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(DownloadState.waiting_link)
async def process_download(message: Message, state: FSMContext, bot: Bot):
    link = message.text.strip() if message.text else ""
    if not link or ("youtube.com" not in link and "youtu.be" not in link):
        await message.answer("⚠️ Пришли корректную YouTube-ссылку.")
        return

    is_vip = await check_vip_status(message.from_user.id)
    if not is_vip:
        await message.answer("❌ VIP истёк. Скачивание недоступно.", reply_markup=main_menu_kb())
        await state.clear()
        return

    await message.answer("⏳ Начинаю скачивание... Это может занять несколько минут.\nПосле скачивания файл будет загружен в облако.")
    await state.clear()

    # Скачивание через yt-dlp + загрузка в R2
    try:
        import yt_dlp
        import tempfile
        from utils.storage import is_r2_configured, upload_to_r2

        ydl_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "outtmpl": os.path.join(tempfile.gettempdir(), f"movie_{message.from_user.id}_%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "max_filesize": MAX_DOWNLOAD_SIZE_GB * 1024 * 1024 * 1024,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info)
            # Иногда расширение может отличаться
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in [".mp4", ".mkv", ".webm"]:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break

        if not os.path.exists(filename):
            await message.answer("❌ Не удалось скачать файл.", reply_markup=main_menu_kb())
            return

        filesize_mb = os.path.getsize(filename) // (1024 * 1024)
        title = info.get("title", "фильм")
        video_id = info.get("id", "unknown")

        # Если R2 настроен — загружаем туда и отдаём ссылку
        if is_r2_configured():
            await message.answer(f"☁️ Загружаю в облако ({filesize_mb} МБ)...")
            object_key = f"movies/{message.from_user.id}_{video_id}.mp4"
            public_url = upload_to_r2(filename, object_key)

            # Удаляем локальный файл в любом случае
            try:
                os.remove(filename)
            except Exception:
                pass

            if public_url:
                await message.answer(
                    f"✅ <b>{title}</b>\n\n"
                    f"📦 Размер: ~{filesize_mb} МБ\n"
                    f"📥 <b>Скачать:</b>\n{public_url}\n\n"
                    f"Ссылка действует постоянно.",
                    reply_markup=main_menu_kb(),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            else:
                await message.answer(
                    f"❌ Не удалось загрузить в облако.\n"
                    f"Попробуй позже или смотри на YouTube:\n{link}",
                    reply_markup=main_menu_kb(),
                )
            return

        # R2 не настроен — пробуем отправить через Telegram (лимит ~50 МБ)
        if filesize_mb > 49:
            try:
                os.remove(filename)
            except Exception:
                pass
            await message.answer(
                f"⚠️ Файл слишком большой ({filesize_mb} МБ).\n"
                f"Лимит Telegram — 50 МБ.\n"
                f"Настрой Cloudflare R2, чтобы скачивать большие файлы.\n\n"
                f"Ссылка на просмотр: {link}",
                reply_markup=main_menu_kb(),
            )
            return

        await message.answer_document(
            document=FSInputFile(filename),
            caption=f"✅ Скачано: {title}",
        )
        try:
            os.remove(filename)
        except Exception:
            pass
        await message.answer("Готово!", reply_markup=main_menu_kb())

    except Exception as e:
        await message.answer(
            f"❌ Ошибка скачивания: {str(e)[:200]}\n"
            f"Попробуй позже или используй ссылку на YouTube.",
            reply_markup=main_menu_kb(),
        )


# ==================== О БОТЕ ====================
@router.callback_query(F.data == "menu:about")
async def menu_about(callback: CallbackQuery):
    text = await get_about_text()
    await callback.message.edit_text(
        f"ℹ️ <b>О боте / сообществе</b>\n\n{text}",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== ПАРТНЁРСТВА ====================
@router.callback_query(F.data == "menu:partner")
async def menu_partner(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "🤝 <b>Партнёрская программа</b>\n\n"
        "Требования:\n"
        "• Instagram — от 1000 подписчиков\n"
        "• TikTok — от 500 подписчиков\n"
        "• YouTube — от 200 подписчиков\n"
        "• Хороший актив и настоящие подписчики\n\n"
        "Что нужно:\n"
        "1. В описании профиля и видео ставить ссылку на бота (можно свою реферальную)\n"
        "2. Вставлять наш 5-секундный рекламный шаблон в свои видео\n\n"
        "Награда: <b>50 ⭐</b> за каждые 10 000 просмотров\n\n"
        "Готов? Нажми кнопку и пришли ссылки на свои соцсети."
    )
    await callback.message.edit_text(text, reply_markup=partner_start_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "partner:ready")
async def partner_ready(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PartnerState.waiting_links)
    await callback.message.edit_text(
        "📎 Пришли ссылки на свои соцсети (Instagram / TikTok / YouTube),\n"
        "которые будут рекламировать нас.\n\n"
        "Можно одной строкой или несколькими сообщениями.",
        reply_markup=back_to_menu_kb()
    )
    await callback.answer()


@router.message(PartnerState.waiting_links)
async def partner_links(message: Message, state: FSMContext):
    links = message.text.strip()
    if len(links) < 10:
        await message.answer("Пришли полноценные ссылки на соцсети.")
        return

    await add_partner(
        user_id=message.from_user.id,
        username=message.from_user.username,
        social_links=links
    )
    await state.clear()

    # Отправляем шаблон (если есть файл, иначе текст)
    template_path = os.path.join("data", "partner_ad_template.mp4")
    if os.path.exists(template_path):
        await message.answer_video(
            video=FSInputFile(template_path),
            caption=(
                "✅ Ссылки приняты!\n\n"
                "📹 Вот рекламный 5-секундный шаблон.\n"
                "Вставляй его в свои видео.\n"
                "Не забудь поставить ссылку на бота в описание!\n\n"
                "Когда наберёшь 10к просмотров — напиши админу для начисления 50 ⭐."
            )
        )
    else:
        await message.answer(
            "✅ Ссылки приняты и отправлены на проверку!\n\n"
            "📹 Рекламный 5-секундный шаблон появится здесь после того, "
            "как админ загрузит файл <code>data/partner_ad_template.mp4</code>.\n\n"
            "Пока используй текст:\n"
            "«Смотри лучшие нарезки кино в нашем боте!»\n\n"
            "Не забудь поставить ссылку на бота в описание профиля и видео.\n"
            "За каждые 10 000 просмотров — 50 ⭐.",
            parse_mode="HTML",
            reply_markup=main_menu_kb()
        )
    await message.answer("Спасибо, что становишься партнёром! 🚀", reply_markup=main_menu_kb())
