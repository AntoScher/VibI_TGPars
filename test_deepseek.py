
import asyncio
from deepseek import generate_summary, DeepseekError

async def main():
    test_text = "Это простой тестовый текст для проверки функции суммирования. Мы хотим увидеть, сможет ли модель Deepseek обработать этот запрос и вернуть осмысленную краткую сводку."
    print("--- Testing Deepseek summary generation ---")
    try:
        summary = await generate_summary(test_text)
        print("Successfully generated summary:")
        print(summary)
    except DeepseekError as e:
        print(f"An error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
