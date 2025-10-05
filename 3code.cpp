#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstdint>
#include <algorithm>

#pragma pack(push, 1)
struct BITMAPFILEHEADER {
    uint16_t bfType;
    uint32_t bfSize;
    uint16_t bfReserved1;
    uint16_t bfReserved2;
    uint32_t bfOffBits;
};

struct BITMAPINFOHEADER {
    uint32_t biSize;
    int32_t biWidth;
    int32_t biHeight;
    uint16_t biPlanes;
    uint16_t biBitCount;
    uint32_t biCompression;
    uint32_t biSizeImage;
    int32_t biXPelsPerMeter;
    int32_t biYPelsPerMeter;
    uint32_t biClrUsed;
    uint32_t biClrImportant;
};

struct RGBQUAD {
    uint8_t rgbBlue;
    uint8_t rgbGreen;
    uint8_t rgbRed;
    uint8_t rgbReserved;
};
#pragma pack(pop)

class BMPRLECompressor {
private:
    BITMAPFILEHEADER fileHeader;
    BITMAPINFOHEADER infoHeader;
    std::vector<RGBQUAD> palette;
    std::vector<uint8_t> pixelData;
    std::vector<uint8_t> compressedData;

public:
    bool loadBMP(const std::string& filename) {
        std::ifstream file(filename, std::ios::binary);
        if (!file) {
            std::cout << "Ошибка: Не удалось открыть файл " << filename << std::endl;
            return false;
        }

        // Чтение заголовков
        file.read(reinterpret_cast<char*>(&fileHeader), sizeof(fileHeader));
        file.read(reinterpret_cast<char*>(&infoHeader), sizeof(infoHeader));

        // Проверка формата BMP
        if (fileHeader.bfType != 0x4D42) { // 'BM'
            std::cout << "Ошибка: Не BMP файл" << std::endl;
            return false;
        }

        // Проверка на 16-цветный формат
        if (infoHeader.biBitCount != 4) {
            std::cout << "Ошибка: Файл не в 16-цветном формате (требуется 4 бита на пиксель)" << std::endl;
            return false;
        }

        // Проверка на сжатие
        if (infoHeader.biCompression != 0) {
            std::cout << "Ошибка: Файл уже сжат" << std::endl;
            return false;
        }

        // Чтение палитры (16 цветов)
        palette.resize(16);
        file.read(reinterpret_cast<char*>(palette.data()), 16 * sizeof(RGBQUAD));

        // Чтение данных пикселей
        file.seekg(fileHeader.bfOffBits, std::ios::beg);
        
        int width = infoHeader.biWidth;
        int height = abs(infoHeader.biHeight);
        int widthInBytes = (width + 1) / 2; // Байт на строку без выравнивания
        int stride = (widthInBytes + 3) & ~3; // Байт на строку с выравниванием
        
        pixelData.resize(stride * height);
        file.read(reinterpret_cast<char*>(pixelData.data()), stride * height);

        if (!file) {
            std::cout << "Ошибка чтения данных изображения" << std::endl;
            return false;
        }

        std::cout << "Файл загружен успешно: " << infoHeader.biWidth << "x" << abs(infoHeader.biHeight) 
                  << ", " << (int)infoHeader.biBitCount << " бит на пиксель" << std::endl;
        return true;
    }

    void compressRLE4() {
        int width = infoHeader.biWidth;
        int height = abs(infoHeader.biHeight);
        int widthInBytes = (width + 1) / 2;
        int stride = (widthInBytes + 3) & ~3;
        
        compressedData.clear();

        // Обрабатываем строки в правильном порядке (BMP хранится снизу вверх)
        for (int y = height - 1; y >= 0; y--) {
            int rowStart = y * stride;
            std::vector<uint8_t> rowWithoutPadding(pixelData.begin() + rowStart, 
                                                  pixelData.begin() + rowStart + widthInBytes);
            compressScanline(rowWithoutPadding, width);
        }

        // Маркер конца bitmap
        compressedData.push_back(0x00);
        compressedData.push_back(0x01);

        std::cout << "Сжатие завершено. Исходный размер: " << pixelData.size() 
                  << " байт, сжатый размер: " << compressedData.size() 
                  << " байт" << std::endl;
        
        if (pixelData.size() > 0) {
            double ratio = (1.0 - (double)compressedData.size() / pixelData.size()) * 100.0;
            std::cout << "Степень сжатия: " << ratio << "%" << std::endl;
        }
    }

private:
    void compressScanline(const std::vector<uint8_t>& scanline, int width) {
        int pos = 0;
        
        while (pos < width) {
            // Ищем последовательность одинаковых пикселей
            int repeatCount = findRepeatSequence(scanline, pos, width);
            
            if (repeatCount >= 3) { // Используем кодирование для 3+ одинаковых пикселей
                // Закодированный режим
                uint8_t pixel = getPixel(scanline, pos);
                uint8_t colorByte = (pixel << 4) | pixel;
                
                compressedData.push_back(static_cast<uint8_t>(repeatCount));
                compressedData.push_back(colorByte);
                pos += repeatCount;
            } else {
                // Абсолютный режим
                int literalCount = findLiteralSequence(scanline, pos, width);
                literalCount = std::min(literalCount, 255);
                
                int byteCount = (literalCount + 1) / 2;
                
                compressedData.push_back(0x00);
                compressedData.push_back(static_cast<uint8_t>(literalCount));
                
                // Записываем пары пикселей
                for (int i = 0; i < byteCount; i++) {
                    int pixelPos = pos + i * 2;
                    uint8_t firstPixel = getPixel(scanline, pixelPos);
                    uint8_t secondPixel = (pixelPos + 1 < width) ? 
                                        getPixel(scanline, pixelPos + 1) : 0;
                    compressedData.push_back((firstPixel << 4) | secondPixel);
                }
                
                // Выравнивание до четного количества байт
                if (byteCount % 2 != 0) {
                    compressedData.push_back(0x00);
                }
                
                pos += literalCount;
            }
        }

        // Маркер конца строки
        compressedData.push_back(0x00);
        compressedData.push_back(0x00);
    }

    int findRepeatSequence(const std::vector<uint8_t>& scanline, int startPos, int maxPos) {
        if (startPos >= maxPos) return 0;
        
        uint8_t firstPixel = getPixel(scanline, startPos);
        int count = 1;
        
        for (int i = startPos + 1; i < maxPos && count < 255; i++) {
            if (getPixel(scanline, i) == firstPixel) {
                count++;
            } else {
                break;
            }
        }
        
        return count;
    }

    int findLiteralSequence(const std::vector<uint8_t>& scanline, int startPos, int maxPos) {
        int count = 1;
        
        for (int i = startPos + 1; i < maxPos && count < 255; i++) {
            // Проверяем, не начинается ли последовательность из 3+ одинаковых пикселей
            if (i + 2 < maxPos && 
                getPixel(scanline, i) == getPixel(scanline, i + 1) &&
                getPixel(scanline, i) == getPixel(scanline, i + 2)) {
                break;
            }
            count++;
        }
        
        return count;
    }

    uint8_t getPixel(const std::vector<uint8_t>& scanline, int pixelPos) {
        int bytePos = pixelPos / 2;
        uint8_t byte = scanline[bytePos];
        
        if (pixelPos % 2 == 0) {
            return (byte >> 4) & 0x0F;
        } else {
            return byte & 0x0F;
        }
    }

public:
    bool saveCompressedBMP(const std::string& filename) {
        std::ofstream file(filename, std::ios::binary);
        if (!file) {
            std::cout << "Ошибка: Не удалось создать файл " << filename << std::endl;
            return false;
        }

        // Создаем новые заголовки для RLE4-сжатого BMP
        BITMAPFILEHEADER newFileHeader;
        BITMAPINFOHEADER newInfoHeader;
        
        // Заполняем файловый заголовок
        newFileHeader.bfType = 0x4D42; // 'BM'
        newFileHeader.bfReserved1 = 0;
        newFileHeader.bfReserved2 = 0;
        newFileHeader.bfOffBits = sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER) + 
                                 (16 * sizeof(RGBQUAD));
        
        // Заполняем информационный заголовок
        newInfoHeader.biSize = sizeof(BITMAPINFOHEADER);
        newInfoHeader.biWidth = infoHeader.biWidth;
        newInfoHeader.biHeight = infoHeader.biHeight; // Положительная высота = снизу вверх
        newInfoHeader.biPlanes = 1;
        newInfoHeader.biBitCount = 4;
        newInfoHeader.biCompression = 2; // BI_RLE4
        newInfoHeader.biSizeImage = compressedData.size();
        newInfoHeader.biXPelsPerMeter = 0;
        newInfoHeader.biYPelsPerMeter = 0;
        newInfoHeader.biClrUsed = 16;
        newInfoHeader.biClrImportant = 16;
        
        // Общий размер файла
        newFileHeader.bfSize = newFileHeader.bfOffBits + newInfoHeader.biSizeImage;

        // Записываем заголовки
        file.write(reinterpret_cast<const char*>(&newFileHeader), sizeof(newFileHeader));
        file.write(reinterpret_cast<const char*>(&newInfoHeader), sizeof(newInfoHeader));
        
        // Записываем палитру
        file.write(reinterpret_cast<const char*>(palette.data()), 16 * sizeof(RGBQUAD));
        
        // Записываем сжатые данные
        file.write(reinterpret_cast<const char*>(compressedData.data()), compressedData.size());

        if (!file) {
            std::cout << "Ошибка записи файла" << std::endl;
            return false;
        }

        std::cout << "Сжатый BMP файл сохранен как: " << filename << std::endl;
        std::cout << "Размер файла: " << newFileHeader.bfSize << " байт" << std::endl;
        return true;
    }
};

int main() {
    setlocale(LC_ALL, "Russian");
    
    std::cout << "BMP RLE архиватор" << std::endl;
    std::cout << "==================" << std::endl;
    std::cout << "Программа создает BMP файл со сжатием RLE" << std::endl;
    std::cout << "Требования к входному файлу:" << std::endl;
    std::cout << "- Формат BMP" << std::endl;
    std::cout << "- 16 цветов (4 бита на пиксель)" << std::endl;
    std::cout << std::endl;

    BMPRLECompressor compressor;
    
    // Запрос имени файла
    std::string filename;
    std::cout << "Введите имя BMP файла для сжатия: ";
    std::cin >> filename;

    // Загрузка и проверка файла
    if (!compressor.loadBMP(filename)) {
        std::cout << "Нажмите Enter для выхода...";
        std::cin.ignore();
        std::cin.get();
        return 1;
    }

    // Сжатие
    compressor.compressRLE4();

    // Сохранение результата
    std::string outputFilename;
    std::cout << "Введите имя для сжатого файла: ";
    std::cin >> outputFilename;

    // Добавляем расширение .bmp если его нет
    if (outputFilename.size() < 4 || 
        outputFilename.substr(outputFilename.size() - 4) != ".bmp") {
        outputFilename += ".bmp";
    }

    if (!compressor.saveCompressedBMP(outputFilename)) {
        std::cout << "Нажмите Enter для выхода...";
        std::cin.ignore();
        std::cin.get();
        return 1;
    }

    std::cout << std::endl << "Готово! Файл успешно заархивирован с помощью RLE." << std::endl;
    std::cout << "Проверьте файл в программе просмотра изображений." << std::endl;
    std::cout << "Нажмите Enter для выхода...";
    std::cin.ignore();
    std::cin.get();
    
    return 0;
}