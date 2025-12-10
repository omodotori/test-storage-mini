#!/bin/bash

echo "🧪 Running tests..."
echo ""

# Запуск тестов с подробным выводом
pytest -v --tb=short

# Проверка результата
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
else
    echo ""
    echo "❌ Some tests failed!"
    exit 1
fi