@echo off
chcp 65001 > nul

echo Запуск 1 команды... add -A
echo.
git add -A

echo Ожидание 1 секунд...
timeout /t 1 /nobreak > nul

echo Запуск 2 команды... commit -m "result"
echo.
git commit -m "result"

echo Ожидание 1 секунд...
timeout /t 1 /nobreak > nul

echo Запуск 3 команды... push
echo.
git push

echo.
echo Все команды выполнены!
pause