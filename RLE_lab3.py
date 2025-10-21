def rle_encode(data):
    list_data = []
    for i in range(0, len(data), 2):
        byte_str = data[i:i+2]
        list_data.append(int(byte_str, 16))
    result = []
    i = 0
    n = len(list_data)
    
    while i < n:
        # Ищем последовательность одинаковых байтов
        current_byte = list_data[i]
        count = 1
        
        # Считаем количество подряд идущих одинаковых байтов (максимум 63)
        while i + count < n and list_data[i + count] == current_byte and count < 63:
            count += 1
        
        if count >= 2:
            result.append(0xC0 + count)
            result.append(current_byte)
            i += count
        else:
            if current_byte >= 0xC0:
                result.append(0xC1)  # Счетчик = 1
                result.append(current_byte)
            else:
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
                result.extend([data_byte] * (count-1))
            i += 1
        else:
            # Обычный байт
            result.append(current_byte)
            i += 1
    
    # Конвертируем результат в hex-строку
    return ''.join(f'{b:02X}' for b in result)


if __name__ == "__main__":
    input_data= "0000000000000111111111111111111111FFFFFFA0000A12DDDB1B1B1B1B1B1BC1C0"
    encoded_data = "25369568C426B3A7C9EFD196"
    print("Упаковка данных:")
    print(f"Исходные данные: {input_data}")
    final_code = rle_encode(input_data)
    print(f"Сжатые данные:   {final_code}")
    print("\nРаспаковка данных")
    print(f"Сжатые данные:   {encoded_data}")
    first_data = rle_decode(encoded_data)
    print(f"Распакованные данные: {first_data}")