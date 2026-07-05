import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, GROUP_ID
from database import init_db, add_report, get_fuel, get_all_recent, get_stats
from parser import parse_fuel_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)
dp = Dispatcher()


@dp.message(F.chat.id == GROUP_ID, F.text)
async def handle_group_message(message: types.Message):
    """Слушает группу и парсит сообщения про бензин"""
    if not message.text:
        return

    parsed = parse_fuel_message(message.text)
    if not parsed:
        return

    report_id = add_report(
        station=parsed["station"],
        fuel_type=parsed["fuel_type"],
        price=parsed["price"],
        address=parsed["address"],
        available=parsed["available"],
        user_id=message.from_user.id,
        username=message.from_user.username or "anon",
    )

    log.info(f"Новый отчёт #{report_id}: {parsed}")

    status = "✅ Есть" if parsed["available"] else "❌ Нет"
    price_str = f" по **{parsed['price']}₽**" if parsed["price"] else ""
    addr_str = f"\n📍 {parsed['address']}" if parsed["address"] else ""

    await message.reply(
        f"📝 **Записал #{report_id}**\n\n"
        f"⛽ **{parsed['fuel_type']}** — {status}{price_str}\n"
        f"🏪 {parsed['station']}{addr_str}\n"
        f"🕐 Только что от @{message.from_user.username or 'anon'}",
        parse_mode=ParseMode.MARKDOWN
    )


@dp.message(Command("where"))
async def cmd_where(message: types.Message):
    """Где есть указанное топливо"""
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "**Использование:**\n"
            "`/where 92` `95` `98` `100`\n"
            "`/where дт` `газ`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    query = args[1].lower()
    fuel_map = {
        "92": "АИ-92",
        "95": "АИ-95",
        "98": "АИ-98",
        "100": "АИ-100",
        "дт": "ДТ",
        "дизель": "ДТ",
        "диз": "ДТ",
        "солярка": "ДТ",
        "газ": "Газ",
        "пропан": "Газ",
        "метан": "Газ",
    }

    fuel_type = fuel_map.get(query)
    if not fuel_type:
        await message.answer(
            "🤷 Не понял топливо. Попробуй:\n"
            "`/where 95` `/where 92` `/where дт`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    rows = get_fuel(fuel_type, hours=24, only_available=True)

    if not rows:
        await message.answer(
            f"😔 По **{fuel_type}** в Волгограде пока ничего нет за 24ч.\n\n"
            f"Стань первым — напиши в группу!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    response = f"⛽ **{fuel_type}** в Волгограде (за 24ч):\n\n"
    seen = set()
    count = 0
    for row in rows:
        station, address, fuel, price, username, created_at = row
        if station in seen:
            continue
        seen.add(station)
        count += 1
        if count > 15:
            break

        try:
            dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            time_str = dt.strftime("%H:%M")
        except (ValueError, TypeError):
            time_str = "—"

        price_str = f" — **{price}₽**" if price else ""
        addr_str = f"\n   📍 {address}" if address else ""

        response += (
            f"**{count}. {station}**{price_str}\n"
            f"   🕐 {time_str} от @{username or 'anon'}{addr_str}\n\n"
        )

    response += f"📊 Всего: {len(rows)} отчётов от {len(seen)} заправок"
    await message.answer(response, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("all"))
async def cmd_all(message: types.Message):
    """Все отчёты за 24 часа"""
    rows = get_all_recent(hours=24)

    if not rows:
        await message.answer("😔 За последние 24ч пока ничего нет.")
        return

    by_fuel = {}
    for row in rows:
        station, address, fuel, price, available, username, created_at = row
        if fuel not in by_fuel:
            by_fuel[fuel] = []
        by_fuel[fuel].append({
            "station": station,
            "available": available,
            "price": price,
        })

    response = "📊 **Сводка за 24ч**\n\n"
    for fuel in sorted(by_fuel.keys()):
        items = by_fuel[fuel]
        unique = {x["station"]: x for x in items if x["available"]}
        response += f"⛽ **{fuel}** — {len(items)} отчётов:\n"
        for i, (station, item) in enumerate(list(unique.items())[:5], 1):
            price_str = f" **{item['price']}₽**" if item["price"] else ""
            response += f"   {i}. ✅ {station}{price_str}\n"
        response += "\n"

    response += f"📈 Всего отчётов: {len(rows)}"

    if len(response) > 4000:
        response = response[:4000] + "\n\n... (используй /where)"

    await message.answer(response, parse_mode=ParseMode.MARKDOWN)


@dp.message(Command("help", "start"))
async def cmd_help(message: types.Message):
    """Подсказка по использованию"""
    await message.answer(
        "⛽ **Бот-мониторинг бензина в Волгограде**\n\n"
        "**📝 Как сообщить:**\n"
        "Просто напиши в группу, например:\n"
        "• `Лукойл на ул. Мира есть 95-й, 56.80`\n"
        "• `Газпром по пр-ту Ленина нет дизеля`\n"
        "• `Роснефть АИ-92 55₽ в наличии`\n\n"
        "**🔍 Команды:**\n"
        "`/where 92` `95` `98` `100`\n"
        "`/where дт` `газ`\n"
        "`/all` — вся сводка\n"
        "`/stats` — статистика\n"
        "`/help` — подсказка",
        parse_mode=ParseMode.MARKDOWN
    )


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика базы"""
    stats = get_stats()
    await message.answer(
        f"📊 **Статистика бота**\n\n"
        f"📝 Всего отчётов: **{stats['total']}**\n"
        f"👥 Уникальных пользователей: **{stats['users']}**\n"
        f"🕐 Последний отчёт: **{stats['last'] or '—'}**",
        parse_mode=ParseMode.MARKDOWN
    )


async def main():
    log.info("🚀 Запуск бота...")
    init_db()
    log.info("✅ База инициализирована")
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("✅ Бот запущен и слушает группу")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 Бот остановлен")
