@echo off
chcp 65001 >nul

:: Циклы перебирают все комбинации категорий и номеров
for %%t in (horizontal_lengths, vertical_lengths, diagonal_lengths, short_strokes, rectangle_corners, continuous_turns, parallel_spacing, continuous_closed_contour) do (
    for %%n in (b1, b7, b14, b20) do (
        :: 1. Создаем папку
        md "result_test_monitor_%%n_%%t"
        
        :: 2. Создаем пустой json внутри этой только что созданной папки
        type nul > "result_test_monitor_%%n_%%t\result.json"
    )
)

echo Все 32 папки созданы, внутри каждой сгенерирован пустой result.json!
pause