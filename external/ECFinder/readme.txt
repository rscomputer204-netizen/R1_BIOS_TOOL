	Ecfinder - программа для поиска и автоматического сохранения в файл прошивок мультиконтроллеров (EC), клавиатурных контроллеров (KBC), биосов и их кусков, в любых бинарных файлах: дампы, обновления с оф сайта и тд

 
 И не только!

	Заодно ищет и сохраняет и основные прошивки биоса или его часть и ряд клавиатурных контроллеров (встречаются редко)

	Автоматическое преобразование SPD DDR3 в SPD DDR3L с правкой контрольной суммы: 
Алгоритм срабатывает при открытие файла размером строго 256 байт (размер eeprom SPD 24c02/34c02), 
дальше идет проверка, что это SPD DDR3 и если да - изменяется в DDR3L (с правкой CRC), файл сохраняется в папку исходного файла; если нет - выход
В консольном режиме файл открывать без параметров: ECFinder.exe filepath-путь-к-файлу

Режим mefix:
Исправляет ошибки при открытии прошивок Intel с ME регионом 15.x и 16.x версий в утилитах Intel Flash Image Tool (FIT) и Modular Flash Image Tool (MFIT), типа:
Error 179: [Fit Actions] Failed to parse CSE region. 
Error 10: [Ifwi Actions] Failed to decompose Region. Failed to decompose CSE data.
Error 18: [Ifwi Actions] Failed to generate decomposed files. CSE Region
Error 18: [Ifwi Actions] Failed to generate decomposed files.

ERROR    : Failed to decompose container DescriptorPlugin:PmcStraps
Details: Decomp meta data does not contain a value for PMC_Strap_pmc_smip_GBETSN_DIS_STRAP.
Source: 'DescriptorPlugin:PmcStraps'

используется только для открытия прошивки в утилите, просто патченный файл не шить!
Запустить файл mefix.cmd или через консоль ecfinder.exe -mefix (или ecfinder.exe -mefix путь-имя-файла), указать файл....

Режим skipec:
Пропускает этап поиска прошивок мультиконтроллеров (EC), клавиатурных контроллеров (KBC)

Поддерживает / program features:

- Мультиконтроллеры(EC) ENE, ITE, Nuvoton, MEC
- Клавиатурных контроллеров (KBC) it8171 / it8176 / IT891x 56kb,  it829x 120kb
- PD Type-C ITE885x 64kb
- BIOS update:
AMI "hidden" CSE ME / PMC / PCHC / PHY regions update extracting (*.CSME_xx.x.x.xxxx_extracted_update.bin)

AMI PFAT (*uncut_version.bin is a assembled file from update parts; *cut_version.bin - presumable cutting; one of them could be a full bios region or a complete firmware)
uncut_version это сумма всех модулей внутри апдейта, зачастую это и есть bios_region; второй файл (*cut_version.bin) это уже его гипотетическое дальнейшее преобразование (просто обрезка лишнего до целого размера 16 / 32... мб) 
- частенько это и будет полная прошивка или опять же bios_region

Asus CAP (*.cap... extract from an update)
Lenovo CAP (*.cap... extract from an update)
Insyde h2o update (*.fd, isflash.bin... extract from an update)

Detect (CS)ME region version and Clean, Configured state + TXE region version
Detect Boot Guard Status (ME version 12-18)
Detect EOM (End of Manufacturing) status. Supported ME versions: 15-19
Detect INTEL (saving microcodes to a folder) / AMD CPUID

save OEM Public Key Hash to a ...info.txt file
save Windows license key starting address (HEX) to a ...info.txt file
savw BIOS Region starting offset (HEX) to a ...info.txt file
save Smip/OEMP/OEM_KM to a file

- SPD DDR3 ----> SPD DDR3L
- Fixing CSE region / CSE data errors / PmcStraps in Intel Flash Image Tool 15.x and Modular Flash Image Tool 16.x

Clevo patch (Disable failure mode: fan at maximum, shutdown by timer) - патчит прошивку мультиконтроллера плат Clevo для отключения аварийного режима (кулер(ы) на максимум, выключение по таймеру)

EC ITE non-mirror mode (for HuaQin NB8607, NB8609 and others) - на ряде плат (HuaQin NB8607, NB8609 и др) прошивка мультиконтроллера превращает ноутбук в кирпич, нужно пропатчить прошивку в режим non-mirror, 
чтобы она не тянула свой кусок из флешки с порчей своего содержимого

Использование / How to use:

При простом запуске утилиты будет предложено указать файл путем его перетаскивания в окошко или, нажав Enter, откроется окно выбора файла
Из exe обновлений файл нужно будет сначала извлечь и найти (если есть)
You have to extract and find an update/bios file from *.exe
Open file by drag and drop or window manager (press enter)

Консольный режим работы / Console (CMD):
Usage: ECFinder.exe -x filepath-путь-к-файлу
x = 128, 160, 192, 256, 288, 384, 512, 768, IT5679 or clevo
Example/Пример: ECFinder.exe -128 d:\file.bin


**режим mefix / mefix mode**
ecfinder.exe -mefix
ecfinder.exe -mefix filepath-путь-к-файлу

**режим skipec / skipec mode**
ecfinder.exe -skipec
ecfinder.exe -skipec filepath-путь-к-файлу


Системные требования / Requirements:
Win7x64 и новее
Интернет / Internet !!!