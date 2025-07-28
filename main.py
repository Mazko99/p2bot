import asyncio
from botua import run_ua_bot
from botru import run_ru_bot

async def main():
    await asyncio.gather(
        run_ua_bot(),
        run_ru_bot()
    )

if __name__ == "__main__":
    asyncio.run(main())
