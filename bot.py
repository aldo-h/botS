import os
import asyncio
import logging
import pandas as pd
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

# Вставьте ваш токен Telegram-бота
TOKEN = "8450913787:AAGFDmWAjUc2XQu_4du6z8p_7KXf1V4FYuM"  # Замените на ваш актуальный токен

router = Router()


class CalcStates(StatesGroup):
    waiting_for_grade_category = State()
    waiting_for_file = State()


def get_grade_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 7–10 классы", callback_data="grades_7_10")],
        [InlineKeyboardButton(text="🎓 11–12 классы", callback_data="grades_11_12")]
    ])


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(
        "Привет! Я бот для подсчета рейтинга учеников по процентам.\n"
        "Сначала выберите категорию классов:",
        reply_markup=get_grade_keyboard()
    )
    await state.set_state(CalcStates.waiting_for_grade_category)


@router.callback_query(CalcStates.waiting_for_grade_category, F.data.startswith("grades_"))
async def process_category_choice(callback: CallbackQuery, state: FSMContext):
    category = callback.data.replace("grades_", "")
    await state.update_data(category=category)

    category_name = "7–10 классы" if category == "7_10" else "11–12 классы"
    await callback.message.edit_text(
        f"Выбрана категория: **{category_name}**.\n\n"
        "Теперь отправьте мне Excel-файл (.xlsx) с журналом оценок.",
        parse_mode="Markdown"
    )
    await state.set_state(CalcStates.waiting_for_file)
    await callback.answer()


@router.message(CalcStates.waiting_for_file, F.document)
async def process_excel_file(message: Message, state: FSMContext):
    document = message.document
    if not document.file_name.endswith(('.xlsx', '.xls')):
        await message.answer("Пожалуйста, отправьте документ в формате Excel (.xlsx или .xls).")
        return

    processing_msg = await message.answer("⏳ Обрабатываю файл, проверяю стандарты и считаю рейтинг...")

    file_info = await message.bot.get_file(document.file_id)
    file_path = f"downloaded_{message.from_user.id}.xlsx"
    output_path = f"top_students_result_{message.from_user.id}.xlsx"

    await message.bot.download_file(file_info.file_path, destination=file_path)

    try:
        user_data = await state.get_data()
        category = user_data.get("category")

        # Обрабатываем файл
        calculate_ratings(file_path, category, output_path)

        # Отправляем готовый файл пользователю
        result_file = FSInputFile(output_path)
        await message.answer_document(
            result_file,
            caption="🏆 Готово! Вот таблица с топом учеников (от лучших к остальным):"
        )

    except Exception as e:
        logging.exception(e)
        await message.answer(f"❌ Ошибка при обработке файла: {e}")
    finally:
        await state.clear()
        await message.bot.delete_message(message.chat.id, processing_msg.message_id)

        # Безопасная очистка временных файлов
        for path in [file_path, output_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except PermissionError:
                    pass


def calculate_ratings(file_path: str, category: str, output_path: str):
    # Используем контекстный менеджер with, чтобы Excel-файл сразу закрывался после чтения
    with pd.ExcelFile(file_path) as xls:
        sheet_name = 'Лист1' if 'Лист1' in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(file_path, sheet_name=sheet_name)

    if 'Unnamed: 1' in df.columns:
        class_col = 'Unnamed: 1'
    else:
        class_col = [col for col in df.columns if 'класс' in str(col).lower()][0] if any(
            'класс' in str(col).lower() for col in df.columns) else df.columns[1]

    filtered_rows = []
    for idx, row in df.iterrows():
        class_val = str(row[class_col])
        digits = "".join(filter(str.isdigit, class_val))
        if digits:
            grade_num = int(digits[:2] if len(digits) >= 2 else digits[0])
            if category == "7_10" and (7 <= grade_num <= 10):
                filtered_rows.append(row)
            elif category == "11_12" and (11 <= grade_num <= 12):
                filtered_rows.append(row)

    if filtered_rows:
        df_filtered = pd.DataFrame(filtered_rows)
    else:
        df_filtered = df

    sort_col = 'итог' if 'итог' in df_filtered.columns else df_filtered.columns[-1]
    df_sorted = df_filtered.sort_values(by=sort_col, ascending=False).reset_index(drop=True)

    df_sorted.to_excel(output_path, index=False)


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    print("Бот успешно запущен и ожидает файлы!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())