def rle_encode(data):
    
    # Конвертируем строку в список байтов
    bytes_list = []
    for i in range(0, len(data), 2):
        byte_str = data[i:i+2]
        bytes_list.append(int(byte_str, 16))
    
    result = []
    i = 0
    n = len(bytes_list)
    
    while i < n:
        # Ищем последовательность одинаковых байтов
        current_byte = bytes_list[i]
        count = 1
        
        # Считаем количество подряд идущих одинаковых байтов (максимум 63)
        while i + count < n and bytes_list[i + count] == current_byte and count < 63:
            count += 1
        
        if count >= 2:
            # Кодируем повторяющуюся последовательность
            # Байт-счетчик = 0xC0 + (count - 1)
            result.append(0xC0 + count - 1)
            result.append(current_byte)
            i += count
        else:
            # Одиночный байт
            if current_byte >= 0xC0:
                # "Проблемный" байт - экранируем
                result.append(0xC1)  # Счетчик = 1
                result.append(current_byte)
            else:
                # Обычный байт - записываем как есть
                result.append(current_byte)
            i += 1
    
    # Конвертируем результат в hex-строку
    return ''.join(f'{b:02X}' for b in result)


def rle_decode(encoded_data):
  
    # Конвертируем строку в список байтов
    bytes_list = []
    for i in range(0, len(encoded_data), 2):
        byte_str = encoded_data[i:i+2]
        bytes_list.append(int(byte_str, 16))
    
    result = []
    i = 0
    n = len(bytes_list)
    
    while i < n:
        current_byte = bytes_list[i]
        
        if current_byte >= 0xC0:
            # Это байт-счетчик
            count = current_byte - 0xC0 + 1  # +1 потому что хранится (count-1)
            i += 1
            if i < n:
                data_byte = bytes_list[i]
                # Добавляем count копий data_byte
                result.extend([data_byte] * count)
            i += 1
        else:
            # Обычный байт
            result.append(current_byte)
            i += 1
    
    # Конвертируем результат в hex-строку
    return ''.join(f'{b:02X}' for b in result)


# Тестирование на данных из лабораторной работы
if __name__ == "__main__":
    # Исходные данные для упаковки
    input_data = "0000000000000111111111111111111111FFFFFFA0000A12DDDB1B1B1B1B1B1BC1C0"
    
    # Данные для распаковки
    encoded_data = "25369568C426B3A7C9EFD196"
    
    print("=== УПАКОВКА ===")
    print(f"Исходные данные: {input_data}")
    compressed = rle_encode(input_data)
    print(f"Сжатые данные:   {compressed}")
    
    print("\n=== РАСПАКОВКА ===")
    print(f"Сжатые данные:   {encoded_data}")
    decompressed = rle_decode(encoded_data)
    print(f"Распакованные данные: {decompressed}")