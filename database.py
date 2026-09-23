import os
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, BigInteger
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.future import select
from sqlalchemy import update, delete, func

from config import DATABASE_URL, DEFAULT_VIP_PRICE, VIP_DURATION_DAYS, DATA_DIR

Base = declarative_base()

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)  # Telegram user_id
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    movies_watched = Column(Integer, default=0)
    is_vip = Column(Boolean, default=False)
    vip_until = Column(DateTime, nullable=True)
    referred_by = Column(BigInteger, nullable=True)  # user_id реферера
    referral_earnings = Column(Integer, default=0)  # заработано звёзд с рефералов
    stars_balance = Column(Integer, default=0)  # баланс для выплат партнёрам/рефералам


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(String(100), unique=True, nullable=False)  # кастомный ID
    title = Column(String(500), nullable=False)
    genre = Column(String(255), nullable=True)
    youtube_link = Column(String(500), nullable=False)
    cover_file_id = Column(String(500), nullable=True)  # Telegram file_id обложки
    added_at = Column(DateTime, default=datetime.utcnow)
    downloads_count = Column(Integer, default=0)


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String(255), nullable=True)
    amount = Column(Integer, nullable=False)  # звёзд
    screenshot_file_id = Column(String(500), nullable=True)
    status = Column(String(50), default="pending")  # pending / approved / rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    admin_note = Column(Text, nullable=True)


class Partner(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    social_links = Column(Text, nullable=False)  # JSON или текст ссылок
    status = Column(String(50), default="pending")  # pending / approved / rejected
    total_views = Column(Integer, default=0)
    total_earned = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    vip_price = Column(Integer, default=DEFAULT_VIP_PRICE)
    about_text = Column(Text, default="🎬 Нарезки Кино — лучшие фильмы и сериалы в нарезках!\nПодписывайтесь на наш канал и наслаждайтесь.")


class WatchedMovie(Base):
    __tablename__ = "watched_movies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    movie_db_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    watched_at = Column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Создаём настройки по умолчанию
    async with async_session() as session:
        result = await session.execute(select(Settings).where(Settings.id == 1))
        if not result.scalar_one_or_none():
            session.add(Settings(id=1, vip_price=DEFAULT_VIP_PRICE))
            await session.commit()


async def get_or_create_user(user_id: int, username: str = None, full_name: str = None, referred_by: int = None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                id=user_id,
                username=username,
                full_name=full_name,
                referred_by=referred_by if referred_by != user_id else None
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Обновляем username/full_name если изменились
            if username and user.username != username:
                user.username = username
            if full_name and user.full_name != full_name:
                user.full_name = full_name
            await session.commit()
        return user


async def get_user(user_id: int) -> Optional[User]:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def update_user_vip(user_id: int, days: int = VIP_DURATION_DAYS):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            now = datetime.utcnow()
            if user.is_vip and user.vip_until and user.vip_until > now:
                user.vip_until = user.vip_until + timedelta(days=days)
            else:
                user.is_vip = True
                user.vip_until = now + timedelta(days=days)
            await session.commit()


async def check_vip_status(user_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_vip:
            return False
        if user.vip_until and user.vip_until < datetime.utcnow():
            user.is_vip = False
            await session.commit()
            return False
        return True


async def get_vip_price() -> int:
    async with async_session() as session:
        result = await session.execute(select(Settings).where(Settings.id == 1))
        settings = result.scalar_one_or_none()
        return settings.vip_price if settings else DEFAULT_VIP_PRICE


async def set_vip_price(price: int):
    async with async_session() as session:
        result = await session.execute(select(Settings).where(Settings.id == 1))
        settings = result.scalar_one_or_none()
        if settings:
            settings.vip_price = price
            await session.commit()


async def get_about_text() -> str:
    async with async_session() as session:
        result = await session.execute(select(Settings).where(Settings.id == 1))
        settings = result.scalar_one_or_none()
        return settings.about_text if settings else "О боте"


async def set_about_text(text: str):
    async with async_session() as session:
        result = await session.execute(select(Settings).where(Settings.id == 1))
        settings = result.scalar_one_or_none()
        if settings:
            settings.about_text = text
            await session.commit()


async def add_movie(movie_id: str, title: str, genre: str, youtube_link: str, cover_file_id: str = None) -> Movie:
    async with async_session() as session:
        movie = Movie(
            movie_id=movie_id,
            title=title,
            genre=genre,
            youtube_link=youtube_link,
            cover_file_id=cover_file_id
        )
        session.add(movie)
        await session.commit()
        await session.refresh(movie)
        return movie


async def get_movie_by_id(movie_id: str) -> Optional[Movie]:
    async with async_session() as session:
        result = await session.execute(select(Movie).where(Movie.movie_id == movie_id))
        return result.scalar_one_or_none()


async def search_movies(query: str) -> List[Movie]:
    async with async_session() as session:
        q = f"%{query.lower()}%"
        result = await session.execute(
            select(Movie).where(
                (func.lower(Movie.title).like(q)) |
                (func.lower(Movie.genre).like(q)) |
                (func.lower(Movie.movie_id).like(q))
            ).limit(20)
        )
        return result.scalars().all()


async def delete_movie(movie_id: str) -> bool:
    async with async_session() as session:
        result = await session.execute(select(Movie).where(Movie.movie_id == movie_id))
        movie = result.scalar_one_or_none()
        if movie:
            await session.delete(movie)
            await session.commit()
            return True
        return False


async def get_all_movies() -> List[Movie]:
    async with async_session() as session:
        result = await session.execute(select(Movie).order_by(Movie.added_at.desc()))
        return result.scalars().all()


async def create_payment_request(user_id: int, username: str, amount: int, screenshot_file_id: str) -> PaymentRequest:
    async with async_session() as session:
        req = PaymentRequest(
            user_id=user_id,
            username=username,
            amount=amount,
            screenshot_file_id=screenshot_file_id,
            status="pending"
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)
        return req


async def get_pending_payments() -> List[PaymentRequest]:
    async with async_session() as session:
        result = await session.execute(
            select(PaymentRequest).where(PaymentRequest.status == "pending").order_by(PaymentRequest.created_at.desc())
        )
        return result.scalars().all()


async def process_payment(req_id: int, approve: bool, admin_note: str = None) -> Optional[PaymentRequest]:
    async with async_session() as session:
        result = await session.execute(select(PaymentRequest).where(PaymentRequest.id == req_id))
        req = result.scalar_one_or_none()
        if not req or req.status != "pending":
            return None
        req.status = "approved" if approve else "rejected"
        req.processed_at = datetime.utcnow()
        req.admin_note = admin_note
        await session.commit()
        if approve:
            await update_user_vip(req.user_id)
            # Реферальный бонус
            user = await get_user(req.user_id)
            if user and user.referred_by:
                bonus = int(req.amount * 0.15)
                async with async_session() as s2:
                    res = await s2.execute(select(User).where(User.id == user.referred_by))
                    referrer = res.scalar_one_or_none()
                    if referrer:
                        referrer.referral_earnings += bonus
                        referrer.stars_balance += bonus
                        await s2.commit()
        return req


async def add_partner(user_id: int, username: str, social_links: str) -> Partner:
    async with async_session() as session:
        result = await session.execute(select(Partner).where(Partner.user_id == user_id))
        existing = result.scalar_one_or_none()
        if existing:
            existing.social_links = social_links
            existing.status = "pending"
            await session.commit()
            return existing
        partner = Partner(user_id=user_id, username=username, social_links=social_links)
        session.add(partner)
        await session.commit()
        await session.refresh(partner)
        return partner


async def get_partners() -> List[Partner]:
    async with async_session() as session:
        result = await session.execute(select(Partner).order_by(Partner.created_at.desc()))
        return result.scalars().all()


async def get_all_users_count() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count(User.id)))
        return result.scalar() or 0


async def get_vip_users_count() -> int:
    async with async_session() as session:
        result = await session.execute(
            select(func.count(User.id)).where(User.is_vip == True)
        )
        return result.scalar() or 0


async def get_movies_count() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count(Movie.id)))
        return result.scalar() or 0


async def increment_watched(user_id: int, movie_db_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.movies_watched += 1
            session.add(WatchedMovie(user_id=user_id, movie_db_id=movie_db_id))
            await session.commit()


async def get_days_with_us(user: User) -> int:
    if not user.joined_at:
        return 0
    return (datetime.utcnow() - user.joined_at).days
