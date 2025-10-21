import os
import struct
from collections import namedtuple

BMPHeader = namedtuple('BMPHeader', 'type size reserved1 reserved2 offset')
BMPInfoHeader = namedtuple('BMPInfoHeader', 
                          'size width height planes bit_count compression image_size x_pels y_pels clr_used clr_important')

def read_bmp_headers(file):
    """Чтение заголовков BMP"""
    try:
        header_data = file.read(54)
        if len(header_data) < 54:
            raise ValueError("Файл слишком мал для BMP")
        if header_data[:2] != b'BM':
            raise ValueError("Не BMP формат")
        
        header = BMPHeader(*struct.unpack('<2sIHHI', header_data[:14]))
        info_header = BMPInfoHeader(*struct.unpack('<IiiHHIIiiII', header_data[14:54]))
        
        return header, info_header
    except struct.error as e:
        raise ValueError(f"Ошибка чтения заголовков: {e}")

def compress_rle4_correct(data, width, height):
    """
    Корректная реализация RLE4 сжатия согласно спецификации BMP
    """
    compressed = bytearray()
    stride = (width + 1) // 2
    
    for y in range(abs(height)):
        row_start = y * stride
        row_data = data[row_start:row_start + stride]
        
        x = 0
        while x < width:
            # Находим последовательность одинаковых пикселей
            current_pixel = get_pixel_safe(row_data, x, width)
            count = 1
            
            # Считаем повторяющиеся пиксели
            while (x + count < width and 
                   count < 255 and 
                   get_pixel_safe(row_data, x + count, width) == current_pixel):
                count += 1
            
            if count >= 2:
                # Кодируем повторяющуюся последовательность
                compressed.append(count)
                compressed.append((current_pixel << 4) | current_pixel)
                x += count
            else:
                # Находим последовательность различных пикселей
                abs_count = 0
                absolute_data = bytearray()
                
                while (x + abs_count < width and 
                       abs_count < 255 and 
                       not has_repetition(row_data, x + abs_count, width)):
                    
                    if abs_count + 1 < width:
                        # Два пикселя в одном байте
                        p1 = get_pixel_safe(row_data, x + abs_count, width)
                        p2 = get_pixel_safe(row_data, x + abs_count + 1, width)
                        absolute_data.append((p1 << 4) | p2)
                        abs_count += 2
                    else:
                        # Последний нечетный пиксель
                        p = get_pixel_safe(row_data, x + abs_count, width)
                        absolute_data.append(p << 4)
                        abs_count += 1
                        break
                
                if abs_count > 0:
                    compressed.append(0)
                    compressed.append(abs_count)
                    compressed.extend(absolute_data)
                    # Выравнивание до четного количества байт
                    if len(absolute_data) % 2:
                        compressed.append(0)
                    x += abs_count
                else:
                    # Одиночный пиксель
                    compressed.append(1)
                    compressed.append((current_pixel << 4) | current_pixel)
                    x += 1
        
        # Конец строки
        compressed.extend([0, 0])
    
    # Конец bitmap
    compressed.extend([0, 1])
    return compressed

def get_pixel_safe(row_data, x, width):
    """Безопасное получение пикселя"""
    if x >= width:
        return 0
    idx = x // 2
    if idx >= len(row_data):
        return 0
    shift = 4 if x % 2 == 0 else 0
    return (row_data[idx] >> shift) & 0xF

def has_repetition(row_data, start_x, width):
    """Проверяет, есть ли повторение пикселей начиная с позиции"""
    if start_x + 1 >= width:
        return False
    p1 = get_pixel_safe(row_data, start_x, width)
    p2 = get_pixel_safe(row_data, start_x + 1, width)
    return p1 == p2

def validate_and_fix_headers(header, info_header, compressed_size):
    """Проверяет и корректирует заголовки для RLE4"""
    # Создаем копии с обновленными полями
    new_header = BMPHeader(
        header.type,
        54 + 64 + compressed_size,  # Новый размер файла
        header.reserved1,
        header.reserved2,
        header.offset
    )
    
    new_info_header = BMPInfoHeader(
        info_header.size,
        info_header.width,
        info_header.height,
        info_header.planes,
        info_header.bit_count,
        2,  # RLE4 compression
        compressed_size,  # Новый размер изображения
        info_header.x_pels,
        info_header.y_pels,
        info_header.clr_used,
        info_header.clr_important
    )
    
    return new_header, new_info_header

def main():
    
    try:
        # Получаем абсолютный путь к текущей директории
        current_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"Директория скрипта: {current_dir}")
        
        input_filename = input("Введите название входного BMP файла: ").strip()
        output_filename = input("Введите название выходного BMP файла: ").strip()
        
        # Создаем полный путь к файлам
        input_path = os.path.join(current_dir, input_filename)
        output_path = os.path.join(current_dir, output_filename)
        
        print(f"Ищем файл по пути: {input_path}")
        
        if not os.path.exists(input_path):
            print(f"Ошибка: Файл '{input_path}' не найден.")
            print(f"Доступные файлы: {[f for f in os.listdir(current_dir) if f.endswith('.bmp')]}")
            return
        
        # Используем полные пути для открытия файлов
        with open(input_path, 'rb') as f:
            header, info_header = read_bmp_headers(f)
            
            # Проверки
            if info_header.bit_count != 4:
                raise ValueError("Требуется 16-цветный BMP (4 бита на пиксель)")
            if info_header.compression != 0:
                raise ValueError("Файл уже сжат")
            
            stride = (info_header.width + 1) // 2
            if (stride % 4) != 0:
                raise ValueError("Ширина строки должна быть кратна 4 байтам")
            
            # Чтение палитры
            f.seek(54)
            palette = [f.read(4) for _ in range(16)]
            
            # Чтение данных изображения
            f.seek(header.offset)
            pixel_data = f.read()
            
            print(f"Исходное изображение: {info_header.width}x{abs(info_header.height)}")
            print(f"Размер данных: {len(pixel_data)} байт")
            
            # Сжатие
            compressed_data = compress_rle4_correct(pixel_data, info_header.width, abs(info_header.height))
            
            # Корректировка заголовков
            new_header, new_info_header = validate_and_fix_headers(header, info_header, len(compressed_data))
            
            # Сохранение в директории проекта
            with open(output_path, 'wb') as out_f:
                # Заголовки
                out_f.write(struct.pack('<2sIHHI', *new_header))
                out_f.write(struct.pack('<IiiHHIIiiII', *new_info_header))
                # Палитра
                out_f.write(b''.join(palette))
                # Сжатые данные
                out_f.write(compressed_data)
            
            # Статистика
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(output_path)
            ratio = (1 - compressed_size / original_size) * 100
            
            print(f"Сжатие завершено!")
            print(f"Исходный размер: {original_size} байт")
            print(f"Сжатый размер: {compressed_size} байт")
            print(f"Эффективность сжатия: {ratio:.1f}%")
            print(f"Сжатый файл сохранен как: {output_path}")
            
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()