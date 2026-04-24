"""
Management command to create fake comments for existing villages.
Comments are provided in three languages (uz, ru, en).

Usage:
    python manage.py fake_comments
    python manage.py fake_comments --flush   (delete all existing comments first)
    python manage.py fake_comments --count 5  (number of comments per village, default 3)
"""

import random

from django.core.management.base import BaseCommand

from apps.main.models import Village, Comment


# ── Pool of fake comments ───────────────────────────────────────────
# Each entry: (comment_uz, comment_ru, comment_en,
#              full_name_uz, full_name_ru, full_name_en,
#              who_uz, who_ru, who_en)
COMMENTS_POOL = [
    (
        "Juda go'zal joy! Tabiat manzaralari hayratlanarli. Albatta yana kelaman.",
        "Прекрасное место! Виды природы потрясающие. Обязательно вернусь.",
        "What a beautiful place! The nature views are stunning. Will definitely come back.",
        "Alisher Karimov",
        "Алишер Каримов",
        "Alisher Karimov",
        "Sayyoh, Toshkent",
        "Турист, Ташкент",
        "Tourist, Tashkent",
    ),
    (
        "Mahalliy taomlar juda mazali edi. Mehmonnavozlik yuqori darajada.",
        "Местная еда была очень вкусной. Гостеприимство на высшем уровне.",
        "The local food was delicious. Hospitality was top-notch.",
        "Nilufar Rahimova",
        "Нилуфар Рахимова",
        "Nilufar Rahimova",
        "Bloger",
        "Блогер",
        "Blogger",
    ),
    (
        "Oilam bilan ajoyib dam oldik. Bolalar uchun ham qiziqarli joylar ko'p.",
        "Прекрасно отдохнули с семьёй. Много интересного и для детей.",
        "Had a wonderful family vacation. Lots of fun activities for kids too.",
        "Sherzod Mirzayev",
        "Шерзод Мирзаев",
        "Sherzod Mirzaev",
        "Tadbirkor, Samarqand",
        "Предприниматель, Самарканд",
        "Entrepreneur, Samarkand",
    ),
    (
        "Qishloq hayotini his qilish ajoyib tajriba bo'ldi. Hamma narsadan mamnunman.",
        "Ощутить деревенскую жизнь — прекрасный опыт. Всем доволен.",
        "Experiencing village life was an amazing experience. Loved everything about it.",
        "Malika Usmonova",
        "Малика Усмонова",
        "Malika Usmonova",
        "O'qituvchi, Farg'ona",
        "Учитель, Фергана",
        "Teacher, Fergana",
    ),
    (
        "Tog' manzaralari nafas oladigan darajada chiroyli. Suratga olish uchun ideal joy.",
        "Горные пейзажи захватывают дух. Идеальное место для фотографии.",
        "Mountain views are breathtaking. Perfect spot for photography.",
        "Jasur Toshmatov",
        "Жасур Тошматов",
        "Jasur Toshmatov",
        "Fotograf",
        "Фотограф",
        "Photographer",
    ),
    (
        "Buloq suvi juda toza va salqin. Tabiatda dam olish uchun zo'r joy.",
        "Родниковая вода очень чистая и прохладная. Отличное место для отдыха на природе.",
        "The spring water is crystal clear and refreshing. Great place for a nature retreat.",
        "Dilnoza Abdullayeva",
        "Дилноза Абдуллаева",
        "Dilnoza Abdullayeva",
        "Shifokor, Buxoro",
        "Врач, Бухара",
        "Doctor, Bukhara",
    ),
    (
        "Mehmon uylar juda qulay va toza. Xizmat ko'rsatish a'lo darajada.",
        "Гостевые дома очень удобные и чистые. Обслуживание на высоте.",
        "The guesthouses are very comfortable and clean. Excellent service.",
        "Bobur Nazarov",
        "Бобур Назаров",
        "Bobur Nazarov",
        "Jurnalist",
        "Журналист",
        "Journalist",
    ),
    (
        "Ziyoratgoh juda muqaddas joy. Ruhiy ozuqa oldim.",
        "Святое место. Получил духовную пищу.",
        "A truly sacred place. Found spiritual nourishment here.",
        "Odina Saidova",
        "Одина Саидова",
        "Odina Saidova",
        "Nafaqaxo'r, Namangan",
        "Пенсионерка, Наманган",
        "Retiree, Namangan",
    ),
    (
        "Hunarmandlar ishini ko'rish juda qiziqarli. Suvenir ham sotib oldim.",
        "Наблюдать за работой ремесленников очень интересно. Купил сувениры.",
        "Watching the artisans work was fascinating. Bought some great souvenirs.",
        "Kamol Rahmonov",
        "Камол Рахмонов",
        "Kamol Rahmonov",
        "Talaba, Toshkent",
        "Студент, Ташкент",
        "Student, Tashkent",
    ),
    (
        "Agroturizm dasturi juda maroqli edi. Sog'ish va bog' ishlari bilan shug'ullandik.",
        "Агротуризм был очень увлекательным. Доили коров и работали в саду.",
        "The agro-tourism program was delightful. We milked cows and worked in the orchard.",
        "Feruza Qodirova",
        "Феруза Кодирова",
        "Feruza Qodirova",
        "Uy bekasi, Jizzax",
        "Домохозяйка, Джизак",
        "Homemaker, Jizzakh",
    ),
    (
        "Sharshara manzarasi hayratlanarli! Suv shovqini tinchlantiradigan ta'sir qiladi.",
        "Вид на водопад потрясающий! Шум воды действует умиротворяюще.",
        "The waterfall view is spectacular! The sound of water is so calming.",
        "Sardor Yusupov",
        "Сардор Юсупов",
        "Sardor Yusupov",
        "Muhandis, Navoiy",
        "Инженер, Навои",
        "Engineer, Navoiy",
    ),
    (
        "Ekskursiya juda yaxshi tashkil etilgan. Gid bilimli va samimiy edi.",
        "Экскурсия отлично организована. Гид знающий и приветливый.",
        "The tour was very well organized. The guide was knowledgeable and friendly.",
        "Gulnora Ismoilova",
        "Гулнора Исмоилова",
        "Gulnora Ismoilova",
        "Menejor, Andijon",
        "Менеджер, Андижан",
        "Manager, Andijan",
    ),
    (
        "Yozda kelgandim, havo juda yoqimli edi. Qaytib kuzda ham kelmoqchiman.",
        "Приезжал летом, погода была прекрасная. Хочу вернуться осенью.",
        "Visited in summer, the weather was lovely. Planning to return in autumn.",
        "Ulug'bek Tursunov",
        "Улугбек Турсунов",
        "Ulugbek Tursunov",
        "Dasturchi, Toshkent",
        "Программист, Ташкент",
        "Software developer, Tashkent",
    ),
    (
        "G'or va petrogliflar juda qiziqarli. Tarixni his qilasiz.",
        "Пещеры и петроглифы очень интересные. Чувствуется дыхание истории.",
        "The caves and petroglyphs are fascinating. You can really feel the history.",
        "Aziza Mamatova",
        "Азиза Маматова",
        "Aziza Mamatova",
        "Tarixchi, Samarqand",
        "Историк, Самарканд",
        "Historian, Samarkand",
    ),
    (
        "Ot minib sayohat qilish eng yoqqan faoliyat bo'ldi. Bolalarimga ham yoqdi.",
        "Верховая прогулка была любимым занятием. Детям тоже понравилось.",
        "Horse riding was the best activity. My kids loved it too.",
        "Doniyor Xasanov",
        "Дониёр Хасанов",
        "Doniyor Xasanov",
        "Harbiy xizmatchi",
        "Военнослужащий",
        "Military officer",
    ),
]


class Command(BaseCommand):
    help = "Create fake comments in 3 languages for all existing villages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=3,
            help="Number of comments per village (default: 3)",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing comments before creating new ones",
        )

    def handle(self, *args, **options):
        count = options["count"]

        if options["flush"]:
            deleted, _ = Comment.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f"Flushed {deleted} existing comments."))

        villages = Village.objects.all().order_by("order")
        if not villages.exists():
            self.stderr.write(self.style.ERROR("No villages found. Import villages first."))
            return

        self.stdout.write(f"\n── Adding {count} fake comments to {villages.count()} villages ──\n")

        total = 0
        for village in villages:
            # Pick `count` random comments (allow repeats only if pool is smaller)
            chosen = random.sample(COMMENTS_POOL, min(count, len(COMMENTS_POOL)))
            if count > len(COMMENTS_POOL):
                chosen = [random.choice(COMMENTS_POOL) for _ in range(count)]

            for idx, entry in enumerate(chosen, start=1):
                (comment_uz, comment_ru, comment_en,
                 name_uz, name_ru, name_en,
                 who_uz, who_ru, who_en) = entry

                Comment.objects.create(
                    village=village,
                    comment_uz=comment_uz,
                    comment_ru=comment_ru,
                    comment_en=comment_en,
                    full_name_uz=name_uz,
                    full_name_ru=name_ru,
                    full_name_en=name_en,
                    who_uz=who_uz,
                    who_ru=who_ru,
                    who_en=who_en,
                    order=idx,
                )
                total += 1

            self.stdout.write(f"  [{count} comments] {village.name}")

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(
            f"Done! Created {total} comments for {villages.count()} villages."
        ))
