import subprocess

# Запускаємо два скрипти одночасно
subprocess.Popen(["python", "botua.py"])
subprocess.Popen(["python", "botru.py"])

# Можна додати лог або інфо
print("🔄 Обидва боти запущено. Не закривайте це вікно.")
input("Натисніть Enter для виходу...")
