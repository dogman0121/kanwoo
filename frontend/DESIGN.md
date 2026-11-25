# Дизайн интерфейса Kanwoo

Документ описывает стили и компоновку, которые уже используются во фронтенде Kanwoo. Для нового экрана сначала подбери ближайший существующий пример и переиспользуй его компоненты и значения темы.

## Цвет

Основная тема Material UI использует CSS-переменные с префиксом `--knw-`. Корневой макет инициализирует цветовую схему по классу, а пункт «Тема» в меню переключает системный, светлый и тёмный режимы. В `sx` используй имена из палитры, например `bgcolor: "background.paper"`, чтобы поверхности переключались вместе с темой. [Основная тема](src/constants/themes/main.theme.ts) · [Корневой макет](src/app/layout.tsx) · [Переключатель темы](src/app/_components/userMenu/ThemeSwitch.tsx)

| Роль в палитре | Светлая | Тёмная |
| --- | --- | --- |
| Основной акцент, `primary.main` | `#FFD600` | `#FFD600` |
| Вторичный цвет, `secondary.main` | `#E3E3E3` | `#2B2A2A` |
| Фон страницы, `background.default` | `#F2F2F3` | `#1D1D1D` |
| Фон панелей, `background.paper` | `#FFFFFF` | `#1C1C1C` |
| Основной текст, `text.primary` | `#000000` | `#E1E1E0` |
| Вторичный текст, `text.secondary` | `#606060` | `#BCBCBC` |
| Шапка, `header.main` | `#FFF1AA` | `#06090E` |
| Подвал, `footer.main` | `#E8E8E8` | `#06090E` |

При выделении текста глобальные стили задают жёлтый фон и чёрный текст. [Глобальные стили](src/app/global.css)

## Типографика и размеры

Основной шрифт — Roboto через `--font-roboto`. Для текста и заголовков используй варианты MUI `Typography`.

| Вариант | Размер | Насыщенность | Межстрочный интервал |
| --- | --- | --- | --- |
| `h1` | 24 px | 600 | 1,7 |
| `h2` | 20 px | 600 | 1,5 |
| `h3` | 18 px | 600 | 1,2 |
| `body1` | 14 px | из MUI | из MUI |
| `caption` | 12 px | из MUI | из MUI |

- Шаг отступов — 5 px. Например, `px: 2` задаёт по 10 px с каждой стороны, а `spacing: 3` у MUI Grid задаёт промежуток 15 px.
- Базовый радиус — 6 px. Кнопки имеют радиус 40 px, отступы 5 × 15 px по вертикали и горизонтали соответственно и сохраняют регистр текста. У варианта `outlined` текст использует `text.primary`.
- Поля с обводкой, селекты и меню имеют радиус 12 px. Ниже `md` размер текста внутри `MuiInputBase` составляет 16 px.
- Диалоги по умолчанию имеют ширину 400 px, радиус 20 px и боковые поля по 10 px. Для типовых действий посмотри, подходят ли [AppButton](src/components/app/AppButton.tsx), [AppModal](src/components/app/AppModal.tsx), [AppTabs](src/components/app/AppTabs.tsx) и [AppSnackbar](src/components/app/AppSnackbar.tsx). [Настройки компонентов MUI](src/constants/themes/main.theme.ts)

## Адаптивность и навигация

Точки перелома основной темы в пикселях — `xs` 0, `sm` 600, `md` 900, `lg` 1240, `xl` 1536. Точки перелома управляют CSS внутри раскладки. Вариант общей оболочки выбирается по заголовку `X-Device-Type`, а главная и каталог выбирают компонент страницы по параметру `viewport`. При проверке таких страниц открывай оба варианта устройства и проверяй ширины внутри каждого. [Общая оболочка](src/app/%28default-layout%29/layout.tsx) · [Главная](src/app/%28default-layout%29/page.tsx) · [Каталог](src/app/%28default-layout%29/catalog/page.tsx)

- **Настольная оболочка.** Верхняя панель с логотипом, каталогом, поиском и меню пользователя. Минимальная высота `Toolbar` в теме — 54 px. Для широких страниц каталог и история используют `Container maxWidth="lg"`. [Настольный макет](src/app/%28default-layout%29/_layouts/desktop/Layout.tsx) · [Настольный каталог](src/features/catalog/pages/CatalogPageDesktop.tsx)
- **Мобильная оболочка.** Фиксированная нижняя навигация ведёт на главную, в каталог, списки, историю и меню. Под контентом оставлено 56 px, чтобы панель его не перекрывала. [Мобильный макет](src/app/%28default-layout%29/_layouts/mobile/Layout.tsx)

## Основные экраны

| Экран | Что переиспользовать |
| --- | --- |
| Главная | Промобаннер имеет пропорции 3:1 на настольном экране и 5:4 на мобильном. Для его загрузки есть скелетоны соответствующих размеров. [Настольный баннер](src/features/home/components/sliders/hero/DesktopHeroSlider.tsx) · [Мобильный баннер](src/features/home/components/sliders/hero/MobileHeroSlider.tsx) · [Скелетоны](src/features/home/components/sliders/hero/skeleton/) |
| Каталог | На настольном экране результаты занимают 7 из 10 колонок, закреплённая панель фильтров — 3. На мобильном поиск и выбор раздела остаются сверху, а фильтры открываются в правом `Drawer`. Обе версии используют `Filters` и `MangaResults`. [Настольный каталог](src/features/catalog/pages/CatalogPageDesktop.tsx) · [Мобильный каталог](src/features/catalog/pages/CatalogPageMobile.tsx) |
| Страница манги | Постер и его скелетон имеют пропорции 2:3. На мобильном обложка или фоновое изображение плавно переходят в фон текущей темы, а постер расположен по центру. Для действия чтения есть `ReadingButton`. [Постер](src/features/manga/components/ui/Poster.tsx) · [Скелетон](src/components/poster/PosterSkeleton.tsx) · [Мобильная страница](src/features/manga/pages/MangaMobilePage.tsx) · [Кнопка чтения](src/features/manga/components/ReadingButton.tsx) |

## Читалка

Маршрут главы использует отдельную тему MUI с тёмной палитрой. Акцент остаётся жёлтым (`#FFD600`), панели используют `#141414`, шапка и подвал — `#121212`. В палитре фон `background.default` белый. Основной текст — 14 px, `h1` — 16 px, `h2` — 28 px. [Макет главы](src/app/%28custom-layout%29/chapters/%5Bid%5D/layout.tsx) · [Тема читалки](src/constants/themes/chapter-page.theme.ts)

`KaReader` выбирает вертикальный или горизонтальный режим. Константа `MAX_CHAPTER_WIDTH` задаёт ширину до 640 px для блока главы в вертикальном режиме и используется при расчёте ширины в шапке и подвале. При изменении управления чтением проверь оба режима на узком и широком экранах. [KaReader](src/features/reader/components/KaReader.tsx) · [Блок главы](src/features/reader/readers/vertical/components/ChapterBlock.tsx) · [Константа ширины](src/constants/reader.ts)
