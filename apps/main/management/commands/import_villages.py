"""
Management command to import tourism villages data.
Village data is embedded directly — no Excel file needed on the server.
Images are loaded from the mat/ folder if present.

Usage:
    python manage.py import_villages
    python manage.py import_villages --flush  (delete all existing data first)
    python manage.py import_villages --mat /path/to/mat
"""

import io
import re
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False

from apps.main.models import City, Village, Gallery


# ── 12 Uzbekistan regions (uz names) ────────────────────────────────
ALL_REGIONS = [
    "Andijon",
    "Buxoro",
    "Farg'ona",
    "Jizzax",
    "Namangan",
    "Navoiy",
    "Qashqadaryo",
    "Samarqand",
    "Sirdaryo",
    "Surxondaryo",
    "Toshkent",
    "Xorazm",
]

# ── Mapping: region name → mat/ folder name ─────────────────────────
REGION_FOLDER_MAP = {
    "Andijon":      "Andijon",
    "Buxoro":       "Bukhara",
    "Farg'ona":     "Fergana",
    "Jizzax":       "JIZZAX",
    "Namangan":     "Namangan",
    "Navoiy":       "Navoiy",
    "Qashqadaryo":  "Qashqadaryo",
    "Samarqand":    "Samarkand",
    "Surxondaryo":  "Surxondaryo",
    "Toshkent":     "Tashkent region",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}

# ── Embedded Village Data ────────────────────────────────────────────
# Format: (region, name, desc_uz, desc_ru, desc_en, act_uz, act_ru, act_en, location)
VILLAGES_DATA = [
    ("Andijon", "Imom ota", "Imom ota turizm qishlog'i Andijon viloyatining tog'oldi hududida joylashgan bo'lib, diniy meros va sokin qishloq hayoti uyg'unlashgan. Imom ota ziyoratgohi, atrofidagi bog'lar, g'orlar va shifobaxsh buloqlar ushbu qishloqning asosiy boyligidir.", "Туристическая деревня Имам ота расположена в предгорной зоне Андижанской области и сочетает религиозное наследие с спокойной сельской жизнью. Мазар Имам ота, сады, пещеры и целебные источники являются главными богатствами деревни.", "Imom Ota Tourism Village, in the foothills of Andijan Region, combines religious heritage with a tranquil rural lifestyle. The Imom Ota shrine, surrounding orchards, caves and healing springs are its main attractions.", "Imom ota ziyorati; g'orlarni ko'rish; buloqlarga sayr; mahalliy taomlar; qishloq hayoti bilan tanishish", "Паломничество к Имам ота; осмотр пещер; прогулки к источникам; знакомство с деревенским бытом и местной кухней", "Pilgrimage to Imom Ota; visiting caves and springs; walking in orchards; tasting local food; experiencing village life", "40.546597, 72.608740"),
    ("Andijon", "Shirmonbuloq", "Shirmonbuloq turizm qishlog'i toza buloqlari va yashil tog' manzaralari bilan mashhur. Qishloqda dehqonchilik va chorvachilik saqlanib qolgan bo'lib, mehmonlar tabiat qo'ynida osoyishta dam olishlari va qishloq hayotini his qilishlari mumkin.", "Туристическая деревня Ширмонбулок известна чистыми источниками и зелёными горными пейзажами. Здесь сохранились традиционные земледелие и животноводство, а гости могут отдохнуть в тишине природы.", "Shirmonbuloq Tourism Village is known for its clear springs and green mountain scenery. Traditional farming and livestock breeding are preserved here, offering visitors a calm nature-oriented stay.", "Buloqqa sayr; tog' etagida piyoda yurish; mahalliy ovqatlar; qishloq aholisi bilan suhbat; tabiatni kuzatish", "Прогулки к источникам; пешие прогулки в предгорьях; дегустация местной кухни; общение с жителями; наблюдение за природой", "Walking to the springs; light hikes in the foothills; sampling local food; meeting villagers; enjoying nature", "40.58896336215766, 72.47327113801329"),
    ("Buxoro", "Qo'rg'on", "Qo'rg'on turizm mahallasi Buxoro viloyatida joylashgan bo'lib, qadimiy masjidlar, hammomlar va Xoja Abduxoliq G'ijduvoniy ziyoratgohi bilan mashhur. Hunarmand xonadonlari qadimiy ustalik an'analarini davom ettiradi.", "Туристическая махалля Кургон в Бухарской области известна старинными мечетями, хаммамами и мавзолеем Ходжа Абдухолик Гиждувание. Домашние мастерские продолжают традиции местных ремёсел.", "Qor'gon Tourism Mahalla in Bukhara Region is known for old mosques, bathhouses and the shrine of Khoja Abdukholiq Ghijduvani. Artisan households keep traditional crafts alive.", "Ziyoratgohlarga tashrif; tarixiy masjid va hammomlarni ko'rish; hunarmand ustaxonalariga tashrif; suvenir xaridi", "Посещение мавзолеев; осмотр старинных мечетей и хаммамов; посещение ремесленных мастерских; покупка сувениров", "Visiting shrines; exploring historic mosques and hammams; visiting craft workshops; buying local souvenirs", "40.10607235601642, 64.67970530411499"),
    ("Buxoro", "Shirin", "Shirin etno turizm qishlog'i zamonaviy sharoitga ega o'tovlar, cho'milish havzasi va hunarmand xonadonlari bilan etno-turizm uchun yaratilgan maskan. Bu yerda mehmonlar ko'chmanchi hayot uslubi va milliy taomlarni his qilishlari mumkin.", "Этнодеревня Ширин предлагает юрты с современными условиями, бассейн и дома ремесленников. Гости могут познакомиться с элементами кочевой культуры и местной кухней.", "Shirin Ethno Tourism Village offers yurts with modern facilities, a swimming pool and artisan households, allowing visitors to experience elements of nomadic culture and local food.", "O'tovlarda tunash; etno-muhitni his etish; mahalliy taomlar; hunarmandchilikni tomosha qilish", "Проживание в юртах; этническая атмосфера; дегустация местных блюд; наблюдение за ремёслами", "Staying in yurts; enjoying an ethnic atmosphere; tasting local dishes; observing traditional crafts", "39.9707031, 64.7986371"),
    ("Buxoro", "Qasri Orifon", "Qasri Orifon turizm qishlog'i Buxoro yaqinida joylashgan bo'lib, mehmon uylari, ovqatlanish shoxobchalari va tarixiy meros obyektlari bilan rivojlangan turizm infratuzilmasiga ega. Ziyorat va madaniy turizm uchun qulay manzil.", "Туристическая деревня Касри Арифон расположена недалеко от Бухары и имеет развитую инфраструктуру: гостевые дома, кафе и объекты культурного наследия. Популярна для паломничества и культурного туризма.", "Qasri Orifon Tourism Village near Bukhara has developed tourism facilities, including guesthouses, eateries and many heritage sites, making it a convenient place for pilgrimage and cultural tourism.", "Ziyorat; muzey va tarixiy obyektlarni tomosha qilish; mahalliy taomlar; mehmon uylarida yashash", "Паломничество; посещение музеев и исторических объектов; дегустация местной кухни; проживание в гостевых домах", "Pilgrimage; visiting museums and heritage sites; enjoying local food; staying in guesthouses", "39.79970087124866, 64.53720668775816"),
    ("Buxoro", "Ushot", "Ushot turizm qishlog'ida oilaviy mehmon uylari, hostel va mehmonxona mavjud bo'lib, agroturizm, folklor va gastro-turizm xizmatlari ko'rsatiladi. Mehmonlar qishloq hayoti va madaniyatini amaliy tarzda his qilishlari mumkin.", "В туристической деревне Ушот действуют семейные гостевые дома, хостел и гостиница. Здесь предлагают агротуризм, фольклорные программы и гастрономические впечатления.", "Ushot Tourism Village offers family guesthouses, a hostel and a hotel, along with agro-tourism, folklore and food experiences where visitors can actively experience village life and culture.", "Agroturizm (sog'ish, bog' ishlari); folklor dasturlari; milliy taomlar; gid-ekskursiyalar", "Агротуризм (дойка, садовые работы); фольклорные программы; национальная кухня; экскурсионные услуги", "Agro-tourism (milking, farm work); folklore shows; national dishes; guided tours", "39.74561105001959, 64.23009688111969"),
    ("Buxoro", "O'ba", "O'ba turizm qishlog'ida mehmonxona, xostel va ko'plab oilaviy mehmon uylari mavjud. Qishloq tinch muhitda bo'lib, sayyohlar uchun Buxoro atrofida dam olish va tunab qolish uchun qulay joy hisoblanadi.", "В деревне Оба есть гостиница, хостел и семейные гостевые дома. Спокойная сельская атмосфера делает её удобным местом для отдыха рядом с Бухарой.", "O'ba Tourism Village has a hotel, hostels and many family guesthouses, providing a quiet rural base for visiting the Bukhara area.", "Mehmon uylari va mehmonxonada yashash; qishloq bo'ylab sayr; mahalliy taomlar", "Проживание в гостевых домах и гостинице; прогулки по деревне; местная кухня", "Staying in guesthouses and a hotel; walking around the village; enjoying local cuisine", "39.915242, 64.261104"),
    ("Jizzax", "Duoba", "Duoba turizm mahallasi Jizzax viloyatida joylashgan bo'lib, tabiiy landshaft va sokin qishloq muhiti bilan ajralib turadi. Bu yerda mehmonlar shovqinsiz, oddiy qishloq hayotini his qilishlari mumkin.", "Туристическая махалля Дуоба в Джизакской области выделяется природными ландшафтами и спокойной сельской атмосферой.", "Duoba Tourism Mahalla in Jizzakh Region offers natural landscapes and a quiet village atmosphere, ideal for a simple rural experience.", "Qishloq bo'ylab sayr; tabiatni kuzatish; mahalliy aholi bilan muloqot", "Прогулки по деревне; наблюдение за природой; общение с местными жителями", "Walking through the village; observing nature; talking with local residents", "39.7869098, 68.3919866"),
    ("Jizzax", "Uzunbuloq", "Uzunbuloq turizm mahallasida Sa'd ibn Abu Vaqqos ziyoratgohi, kashtachilik va temirchilik ustaxonalari joylashgan. Ziyorat va hunarmandchilik an'analari uyg'unlashgan.", "В махалле Узунбулок находятся мавзолей Са'д ибн Абу Ваккос, а также мастерские по вышивке и кузнечному делу.", "Uzunbuloq Tourism Mahalla hosts the shrine of Sa'd ibn Abu Waqqos and workshops for embroidery and blacksmithing, combining pilgrimage and crafts.", "Ziyorat; kashtachilik va temirchilik ustaxonasiga tashrif; hunarmandchilik bo'yicha mahorat darslari", "Паломничество; посещение мастерских по вышивке и кузнечному делу; мастер-классы по ремёслам", "Pilgrimage; visiting embroidery and blacksmith workshops; craft masterclasses", "39.900270984065, 67.674009497965"),
    ("Jizzax", "Novqa", "Novqa turizm qishlog'ida Novqa ota ziyoratgohi, kashtachilik va temirchilik ustaxonalari mavjud. Mehmonlar hunarmandchilik va milliy taomlar tayyorlash jarayonini kuzatishlari mumkin.", "В деревне Новка расположены мазар Новка ота и ремесленные мастерские. Гости могут наблюдать за процессом изготовления изделий и национальных блюд.", "Novqa Tourism Village features the Novqa Ota shrine and craft workshops, where visitors can see traditional crafts and cooking.", "Ziyorat; kashtachilik, temirchilik; milliy taomlar tayyorlash bo'yicha namoyishlar", "Паломничество; мастерские по вышивке и ковке; показ приготовления национальных блюд", "Pilgrimage; embroidery and blacksmith workshops; demonstrations of traditional cooking", "39.7448638, 67.7096562"),
    ("Jizzax", "Uxum", "Uxum turizm qishlog'i ekoturizm, etno-turizm va plyaj turizmi bilan mashhur. Milliy tabiat bog'i, qadimiy qo'rg'on, qoya tosh rasmlari va Hazrati Imom ota ziyoratgohi asosiy diqqatga sazovor joylardir.", "Туристическая деревня Ухум известна экотуризмом и этнотуризмом. Здесь находятся национальный природный парк, древняя крепость, петроглифы и мазар Хазрати Имам ота.", "Uxum Tourism Village is known for eco- and ethnotourism, with a national nature park, an ancient fortress, rock carvings and the Hazrati Imom Ota shrine.", "Ekoturizm; piyoda sayohatlar; qoya rasmlari va qo'rg'onni ko'rish; milliy taomlar sayli; ziyorat", "Экотуризм; пешие походы; осмотр петроглифов и крепости; фестиваль национальной кухни; паломничество", "Eco-tourism; hiking; visiting rock carvings and the fortress; local food festival; pilgrimage", "40.579505, 66.7940746"),
    ("Qashqadaryo", "Miraki", "Miraki turizm qishlog'i Hisorak suv ombori yaqinida joylashgan bo'lib, tog' va suv manzaralari bilan mashhur. Sanatoriy, turizm bekati va hunarmandlar uylari mehmonlarga xizmat ko'rsatadi.", "Деревня Мираки расположена рядом с водохранилищем Хисорак и известна горами и водными пейзажами. Здесь есть санаторий, туристическая база и дома ремесленников.", "Miraki Tourism Village lies near the Hisorak reservoir and offers mountain and water landscapes, with a sanatorium, tourism base and artisan houses.", "Suv ombori bo'yicha sayr; tog'larda sayohat; sanatori yordami; hunarmandlar uyiga tashrif", "Прогулки у водохранилища; горные прогулки; санаторное лечение; посещение домов ремесленников", "Walking by the reservoir; mountain walks; sanatorium stays; visiting artisan homes", "39.02589478787358, 67.11145995470035"),
    ("Qashqadaryo", "Qaynar", "Qaynar turizm qishlog'i shifobaxsh buloqlari, sanatoriylar va tog' landshafti bilan mashhur. Etti qiz g'ori va Mingbuloq oromgohi kabi tabiiy obyektlar sog'lomlashtirish turizmi uchun imkon yaratadi.", "Деревня Кайнар известна целебными источниками, санаториями и горными ландшафтами. Пещера «Семь девушек» и зона отдыха Мингбулок привлекают любителей лечебного и природного туризма.", "Qaynar Tourism Village is famous for healing springs, sanatoriums and mountain scenery, including the Etti Qiz cave and Mingbuloq recreation area, ideal for health and nature tourism.", "Shifobaxsh buloqlarda davolanish; sanatoriy xizmatlari; g'orlarga sayr; tog'larda yurish", "Лечение на целебных источниках; услуги санатория; прогулки к пещерам; горные прогулки", "Thermal and spring treatments; sanatorium services; visiting caves; mountain walks", "39.25415, 66.91567"),
    ("Qashqadaryo", "Bashir", "Bashir turizm qishlog'i Hazrati Bashir ziyoratgohi, g'orlar, sharshara va tog' manzaralari bilan ajralib turadi. Ziyorat va ekoturizm birlashtirilgan yo'nalishdir.", "Деревня Башир выделяется мазаром Хазрати Башир, пещерами, водопадом и горными пейзажами. Здесь сочетаются паломничество и экотуризм.", "Bashir Tourism Village features the Hazrati Bashir shrine, caves, a waterfall and mountain views, combining pilgrimage and eco-tourism.", "Ziyorat; g'orlarga sayohat; sharshara va tog' landshaftlariga sayr; suratga olish", "Паломничество; посещение пещер; прогулки к водопаду и в горы; фотосъёмка", "Pilgrimage; visiting caves; walking to the waterfall and mountains; photography", "39.12000, 66.88111"),
    ("Navoiy", "Sentob", "Sentob turizm qishlog'i qadimiy qo'rg'on qoldiqlari, g'orlar, petrogliflar, maqbaralar va sharsharalar bilan mashhur. Tabiyat va tarix uyg'unlashgan noyob maskan.", "Деревня Сентоб известна остатками древней крепости, пещерами, петроглифами, мавзолеями и водопадами. Это уникальное соединение природы и истории.", "Sentob Tourism Village is known for ruins of an ancient fortress, caves, petroglyphs, mausoleums and waterfalls, offering a unique mix of nature and history.", "Qadimiy yodgorliklarni ko'rish; g'or va petrogliflarni tomosha qilish; sharshara va ko'l bo'yicha sayr; ziyorat", "Осмотр древних памятников; посещение пещер и петроглифов; прогулки к водопадам и озёрам; паломничество", "Visiting ancient sites; exploring caves and rock art; walking to waterfalls and lakes; pilgrimage", "40.62457515090464, 66.67811676264652"),
    ("Navoiy", "Langar", "Langar turizm mahallasi Langar ota maqbarasi, g'orlar, sharsharalar va etno-qishloq qiyofasi bilan ajralib turadi. Ziyorat va tabiat manzaralari uchun mashhur joy.", "Туристическая махалля Лангар выделяется мавзолеем Лангар ота, пещерами, водопадами и этнодеревенским обликом.", "Langar Tourism Mahalla is distinguished by the Langar Ota mausoleum, caves, waterfalls and an ethnovillage atmosphere.", "Ziyorat; sharshara va g'orlarga sayr; qishloq ko'rinishida foto va sayr", "Паломничество; прогулки к водопадам и пещерам; фотографирование и прогулки по этнодеревне", "Pilgrimage; walks to waterfalls and caves; strolling and taking photos in the ethnovillage", "40.39344533057751, 65.98445796719922"),
    ("Navoiy", "Chuya", "Chuya turizm mahallasi Talizar qal'asi, tepaliklar, Muz buloq va sharsharalar bilan birga ziplayn va tyubing kabi faol dam olish imkoniyatlarini taklif etadi.", "Туристическая махалля Чуя предлагает посещение крепости Тализар, холмов, источника Муз болон водопада, а также активный отдых — зиплайн и тюбинг.", "Chuya Tourism Mahalla offers visits to Talizar fortress, hills, the Muz spring and waterfall, as well as active leisure such as zipline and tubing.", "Ziplayn va tyubing; qal'a va tepaliklarga chiqish; sharshara va buloqqa sayr; selfi zonalar", "Зиплайн и тюбинг; подъём к крепости и холмам; прогулки к водопаду и источнику; селфи-зоны", "Ziplining and tubing; climbing to the fortress and hills; walking to waterfalls and springs; enjoying selfie spots", "40.45817032847348, 66.04894907009276"),
    ("Navoiy", "Angidon", "Angidon turizm mahallasi ming yillik archa daraxtlari, sharshara, buloqlar va suv tegirmonlari bilan mashhur. Tog' manzaralari va tarixiy uzumzorlar ham diqqatga sazovordir.", "Туристическая махалля Ангидон известна многовековыми можжевельниками, водопадом, источниками и водяными мельницами, а также горными пейзажами и старыми виноградниками.", "Angidon Tourism Mahalla is known for millennia-old juniper trees, a waterfall, springs, water mills, mountain views and historic vineyards.", "Archa o'rmonida sayr; sharshara va buloqlarga borish; suv tegirmonlarini ko'rish; tabiatni kuzatish", "Прогулки в можжевеловом лесу; посещение водопада и источников; осмотр водяных мельниц; наблюдение за природой", "Walking in juniper forests; visiting the waterfall and springs; seeing water mills; enjoying the natural scenery", "40.3201703581658, 65.91509691957367"),
    ("Samarqand", "Konigil", "Konigil turizm qishlog'i Samarqand yaqinida joylashgan bo'lib, Samarqand qog'ozi ishlab chiqarish va hunarmandchilik markazi sifatida mashhur. Qishloq atrofida kanallar va ekin maydonlari joylashgan.", "Деревня Конигил возле Самарканда известна как центр производства самаркандской бумаги и ремёсел. Вокруг расположены каналы и поля.", "Konigil Tourism Village near Samarkand is a centre of traditional Samarkand paper-making and handicrafts, surrounded by canals and fields.", "Qog'oz tayyorlash jarayonini tomosha qilish; hunarmandchilik ustaxonalariga tashrif; qishloq bo'ylab sayr", "Наблюдение за процессом изготовления бумаги; посещение ремесленных мастерских; прогулки по деревне", "Watching traditional paper-making; visiting craft workshops; walking through the village", "39.6664, 67.0339"),
    ("Samarqand", "Bog'ibaland", "Bog'ibaland turizm mahallasi tarixiy bog'lar va an'anaviy uy- hovli madaniyati bilan ajralib turadi. Shaharga yaqin bo'lsa-da, mahalla hayoti va agro-turizm unsurlari saqlangan.", "Туристическая махалля Боги Баланд отличается историческими садами и традиционной культурой дворовых домов. Несмотря на близость к городу, здесь сохранился махаллинский уклад.", "Bog'ibaland Tourism Mahalla is characterised by historic gardens and traditional courtyard houses, preserving mahalla life close to the city.", "Mahallani piyoda kezish; uy hovlilarini ko'rish; mahalliy taomlarni tatib ko'rish; kichik agro-turizm tajribalari", "Пешие прогулки по махалле; знакомство с традиционными домами; дегустация местных блюд; элементы агротуризма", "Walking around the mahalla; seeing traditional houses; tasting local food; small agro-tourism experiences", "39.6881, 67.0050"),
    ("Samarqand", "Tersak", "Tersak turizm qishlog'i tog' etagida joylashgan bo'lib, dehqonchilik va chorvachilikka asoslangan qishloq hayoti saqlangan. Tabiat va qishloq manzaralari sayyohlar uchun jozibali.", "Деревня Терсак расположена в предгорье, где сохранился уклад, основанный на земледелии и скотоводстве. Природные и сельские пейзажи привлекательны для туристов.", "Tersak Tourism Village lies in the foothills, preserving a lifestyle based on farming and herding, with attractive rural and natural scenery.", "Qishloq bo'ylab piyoda yurish; tog' etagida sayr; mahalliy taomlar; qishloq hayoti bilan tanishish", "Пешие прогулки по деревне; прогулки в предгорьях; местная кухня; знакомство с сельским бытом", "Walking around the village; foothill walks; trying local food; observing village life", "39.3806, 67.0397"),
    ("Samarqand", "Oqsoy", "Oqsoy turizm qishlog'i tog'li hududda joylashgan bo'lib, soylar, yashil adirlar va ziyorat joylari bilan mashhur. Ekoturizm va ziyorat turizmi birgalikda rivojlangan.", "Деревня Ок-сой находится в горной местности и известна речками, зелёными холмами и местами паломничества. Здесь развиты экотуризм и религиозный туризм.", "Oqsoy Tourism Village is located in a mountainous area with streams, green hills and pilgrimage sites, combining eco- and religious tourism.", "Tog'larda piyoda yurish; soy bo'yida sayr; ziyorat; mahalliy taomlar", "Горные прогулки; прогулки вдоль речек; паломничество; местная кухня", "Mountain walks; strolling along streams; pilgrimage; local cuisine", "39.5178, 66.6300"),
    ("Samarqand", "Omonqo'ton", "Omonqo'ton turizm mahallasi tog'li hududda joylashgan bo'lib, MTB yo'llari, tabiat manzaralari va ziyorat joylari bilan mashhur. Mahallada mehmon uylari va dam olish infratuzilmasi rivojlanmoqda.", "Туристическая махалля Омон-кутон находится в горах и известна маршрутами для MTB, природными пейзажами и местами паломничества. Инфраструктура гостевых домов постепенно развивается.", "Omonqo'ton Tourism Mahalla is a mountain area known for MTB routes, natural scenery and pilgrimage sites, with growing guesthouse infrastructure.", "MTB va piyoda marshrutlar; tog' sayohatlari; ziyorat; mahalliy uy-mehmonxonalarda tunash", "Маршруты для MTB и пешие тропы; горные прогулки; паломничество; проживание в семейных гостевых домах", "MTB and hiking routes; mountain trips; pilgrimage; staying in family guesthouses", "39.4186, 67.2489"),
    ("Samarqand", "Yangijo'y", "Yangijo'y turizm qishlog'i tog' etagidagi qishloq bo'lib, ekoturizm, agro-turizm va ekstremal yo'nalishlar uchun qulay. Bog'lar va yaylovlar bilan o'ralgan.", "Деревня Янгижуй находится в предгорьях и подходит для экотуризма, агротуризма и элементов экстремального туризма. Окружена садами и пастбищами.", "Yangijo'y Tourism Village in the foothills is suitable for eco-, agro- and light adventure tourism, surrounded by orchards and pastures.", "Ekoturizm; agro-turizm; yengil ekstremal marshrutlar; qishloq bo'ylab sayr", "Экотуризм; агротуризм; лёгкие экстремальные маршруты; прогулки по деревне", "Eco-tourism; agro-tourism; light adventure routes; walking around the village", "39.5594, 66.9396"),
    ("Surxondaryo", "Sangardak", "Sangardak turizm mahallasi mashhur Sangardak sharsharasi bilan tanilgan bo'lib, tog' va daralar bilan o'ralgan. Tabiyat qo'ynida dam olish uchun mashhur manzil.", "Махалля Сангардик известна водопадом Сангардик и окружена горами и ущельями. Популярное место отдыха на природе.", "Sangardak Tourism Mahalla is famous for the Sangardak waterfall and is surrounded by mountains and gorges, making it a popular nature escape.", "Sharsharani tomosha qilish; daralarda piyoda yurish; piknik; suratga olish", "Осмотр водопада; пешие прогулки по ущельям; пикники; фотосъёмка", "Viewing the waterfall; hiking in the gorges; picnics; photography", "38.5589, 67.5656"),
    ("Surxondaryo", "Sina", "Sina turizm qishlog'i Denov tumanidagi qishloq bo'lib, an'anaviy dehqonchilik va qishloq hayoti bilan ajralib turadi. Mehmonlar uchun sokin muhit va mahalliy taomlar taklif etiladi.", "Деревня Сина в Деновском районе отличается традиционным земледелием и сельским укладом жизни. Гостям предлагают спокойную атмосферу и местную кухню.", "Sina Tourism Village in Denov District offers traditional farming life, a calm atmosphere and local food.", "Qishloq bo'ylab sayr; dehqonchilik hayoti bilan tanishish; oilaviy dasturxon", "Прогулки по деревне; знакомство с сельским бытом; семейные трапезы", "Walking around the village; seeing farming life; sharing family-style meals", ""),
    ("Surxondaryo", "Omonxona", "Omonxona turizm qishlog'i Boysun tumanida joylashgan bo'lib, Boysun madaniy hududining bir qismi sifatida tog' va qishloq hayoti uyg'unlashgan. An'anaviy turmush tarzi saqlanib qolgan.", "Деревня Омонхона в Байсунском районе является частью культурного региона Байсун, где сочетаются горы и традиционный сельский быт.", "Omonxona Tourism Village in Boysun District is part of the Boysun cultural area, combining mountain scenery with traditional village life.", "Qishloq hayoti bilan tanishish; tog' etagida sayr; mahalliy taomlar", "Знакомство с сельским бытом; прогулки в предгорьях; местная кухня", "Experiencing village life; walking in the foothills; trying local dishes", ""),
    ("Surxondaryo", "Nilu", "Nilu turizm qishlog'i Sariosiyo tumanida joylashgan bo'lib, tog' etagidagi tinch qishloq muhiti bilan ajralib turadi. Dehqonchilik va kundalik qishloq turmushi asosiy hayot tarzidir.", "Деревня Нилу в Сариосийском районе отличается спокойной предгорной сельской атмосферой, основанной на земледелии и повседневной деревенской жизни.", "Nilu Tourism Village in Sariosiyo District offers a peaceful foothill village atmosphere based on farming and everyday rural life.", "Qishloq bo'ylab sayr; dehqonchilik hayotini kuzatish; mahalliy taomlar", "Прогулки по деревне; наблюдение за земледелием; местная кухня", "Walking around the village; observing farming; enjoying local cuisine", ""),
    ("Surxondaryo", "Chorbog'", "Chorbog' turizm qishlog'i Sherobod tumanida bo'lib, tog' va qishloq manzaralari bilan ajralib turadi. Tabiat qo'ynida sokin dam olish uchun mos.", "Деревня Чарбог в Шерабадском районе выделяется горными и сельскими пейзажами и подходит для спокойного отдыха на природе.", "Chorbog' Tourism Village in Sherobod District offers mountain and rural scenery, suitable for a quiet nature-oriented stay.", "Tabiatda dam olish; qishloq bo'ylab sayr; mahalliy aholi bilan muloqot", "Отдых на природе; прогулки по деревне; общение с местными жителями", "Resting in nature; walking in the village; meeting local residents", ""),
    ("Surxondaryo", "Sayrob", "Sayrob turizm qishlog'i Boysun tumanida joylashgan bo'lib, Boysun tog' va qishloq madaniyatining bir qismi hisoblanadi. An'anaviy turmush tarzi va tabiiy manzaralar mehmonlarni jalb etadi.", "Деревня Сайроб в Байсунском районе является частью горного и сельского культурного пространства Байсун. Сохранились традиционный быт и природные пейзажи.", "Sayrob Tourism Village in Boysun District forms part of the Boysun mountain and rural cultural area, with traditional lifestyle and natural landscapes.", "Qishloq hayoti; tog' etagida sayr; mahalliy taomlar; madaniy muloqot", "Сельский быт; прогулки в предгорьях; местная кухня; культурное общение", "Experiencing rural life; foothill walks; local cuisine; cultural exchange", ""),
    ("Toshkent", "Ovjazsoy", "Ovjazsoy turizm qishlog'i tog'li hududda joylashgan bo'lib, Hazrati Ali ziyoratgohi, dam olish maskanlari va uy hayvonot bog'i bilan mashhur. Tabiat va ziyorat uyg'unlashgan.", "Деревня Овжасой расположена в горах и известна мазаром Хазрати Али, зонами отдыха и небольшим зоопарком домашних животных.", "Ovjazsoy Tourism Village is located in the mountains and is known for the Hazrati Ali shrine, recreation areas and a small domestic animal zoo.", "Ziyorat; tog'larda sayr; dam olish maskanlariga borish; hayvonlar bilan tanishish", "Паломничество; прогулки в горах; посещение зон отдыха; знакомство с домашними животными", "Pilgrimage; mountain walks; visiting recreation spots; meeting domestic animals", "40.819551, 69.963707"),
    ("Toshkent", "Ertoshsoy", "Ertoshsoy turizm qishlog'i ko'plab mehmon uylari, Arashan ko'llari va Kelinchak vodiysiga chiqish yo'llari bilan mashhur. Qadimiy qoyatosh rasmlarini ko'rish mumkin.", "Деревня Эртошсой славится многочисленными гостевыми домами, маршрутами к озёрам Арашан и Долине невест, а также древними петроглифами.", "Ertoshsoy Tourism Village is known for its many guesthouses, access to the Arashan lakes and Kelinchak valley, and ancient rock paintings.", "Trekking va piyoda yurish; ko'llarga va vodiyga sayohat; qoyatosh rasmlarini tomosha qilish; mehmon uylarda yashash", "Треккинг и пешие походы; путешествия к озёрам и в долину; осмотр петроглифов; проживание в гостевых домах", "Trekking and hiking; trips to lakes and the valley; viewing rock art; staying in guesthouses", "41.140308, 70.362902"),
    ("Toshkent", "Chashma", "Chashma turizm qishlog'i Chatqol biosfera qo'riqxonasi kirish qismida joylashgan bo'lib, ekoturizm va agroturizm uchun qulay. Mehmon uylari, hostel va sanatoriy mavjud.", "Деревня Чашма расположена у входа в Чаткальский биосферный заповедник и подходит для эко- и агротуризма. Здесь есть гостевые дома, хостел и санаторий.", "Chashma Tourism Village sits at the entrance to the Chatkal Biosphere Reserve and is suitable for eco- and agro-tourism, with guesthouses, a hostel and a sanatorium.", "Ekoturizm; agroturizm; o'rmon bo'ylab sayr; sanatori xizmatlari; mehmon uylari", "Экотуризм; агротуризм; прогулки по лесу; санаторные услуги; проживание в гостевых домах", "Eco-tourism; agro-tourism; forest walks; sanatorium services; staying in guesthouses", "41.24617582265431, 69.75437375927261"),
    ("Toshkent", "Kumushkon", "Kumushkon turizm qishlog'i tog'li hududda joylashgan bo'lib, ko'plab mehmon uylari, dam olish maskanlari va ekoturizm obyektlariga ega. Toshkentdan qisqa dam olish uchun mashhur yo'nalish.", "Деревня Кумушкон находится в горах и имеет множество гостевых домов, зон отдыха и объектов экотуризма. Популярное направление для краткого отдыха из Ташкента.", "Kumushkon Tourism Village lies in the mountains with many guesthouses, resorts and eco-tourism facilities, popular for short breaks from Tashkent.", "Mehmon uylari va dam olish maskanlarida tunash; tog'larda sayr; ekoturizm faoliyatlari", "Проживание в гостевых домах и зонах отдыха; горные прогулки; занятия экотуризмом", "Staying in guesthouses and resorts; mountain walks; eco-tourism activities", ""),
    ("Toshkent", "Yakkatut", "Yakkatut turizm qishlog'i ko'plab mehmon uylari, ekoturizm va agroturizm obyektlari, gid va transport xizmati, savdo va folklor dasturlari bilan kompleks turizm maskani hisoblanadi.", "Деревня Яккатут — комплексный туристический центр с многочисленными гостевыми домами, объектами эко- и агротуризма, услугами гидов и транспорта, торговлей и фольклорными программами.", "Yakkatut Tourism Village is a comprehensive tourism centre with many guesthouses, eco- and agro-tourism sites, guide and transport services, shops and folklore programmes.", "Ekoturizm; agroturizm; ot va suv transportida sayr; folklor va hunarmandchilik; mahalliy taomlar", "Экотуризм; агротуризм; прогулки на лошадях и по воде; фольклор и ремёсла; местная кухня", "Eco- and agro-tourism; horse and water-based rides; folklore and crafts; local cuisine", "41.613085, 70.091626"),
    ("Namangan", "Nanay", "Nanay turizm qishlog'i tog'lar va daralar bilan o'ralgan bo'lib, yozgi dam olish, ekoturizm va ekstremal faoliyatlar uchun mashhur. Ko'plab mehmon uylari va ovqatlanish maskanlari mavjud.", "Деревня Нанай, окружённая горами и ущельями, известна летним отдыхом, экотуризмом и активными видами досуга. Здесь много гостевых домов и заведений питания.", "Nanay Tourism Village, surrounded by mountains and gorges, is popular for summer holidays, eco-tourism and active recreation, with many guesthouses and eateries.", "Tog'larda yurish; ziplayn; ot minib sayr; ekoturizm; mahalliy taomlar", "Горные прогулки; зиплайн; верховые прогулки; экотуризм; местная кухня", "Mountain walks; zipline; horse riding; eco-tourism; local food", "41.51349932773204, 71.70279212774683"),
    ("Namangan", "Chodak", "Chodak turizm qishlog'i katta turizm salohiyatiga ega bo'lib, yuzlab oilaviy mehmon uylari, osma yo'llar, ziyoratgohlar va ekoturizm obyektlari bilan mashhur.", "Деревня Чодак обладает большим туристическим потенциалом: сотни семейных гостевых домов, подвесные тропы, места паломничества и объекты экотуризма.", "Chodak Tourism Village has high tourism potential with hundreds of family guesthouses, suspension paths, pilgrimage sites and eco-tourism facilities.", "Oilaviy mehmon uylarda tunash; tog'larda sayr; osma yo'l bo'ylab yurish; ziyorat; ekoturizm", "Проживание в семейных гостевых домах; горные прогулки; прогулки по подвесным тропам; паломничество; экотуризм", "Staying in family guesthouses; mountain walks; walking on suspension paths; pilgrimage; eco-tourism", "40.97958123513377, 70.75151041313143"),
    ("Namangan", "Oromgoh", "Oromgoh turizm mahallasi ko'plab oilaviy mehmon uylari, hostel va sanatoriylar bilan sog'lomlashtirish va dam olish turizmi uchun rivojlangan. Tabiat qo'ynida sokin dam olish imkonini beradi.", "Туристическая махалля Оромгох с многочисленными семейными гостевыми домами, хостелами и санаториями развита как центр оздоровительного и рекреационного туризма.", "Oromgoh Tourism Mahalla, with many family guesthouses, hostels and sanatoriums, is developed for health and recreational tourism in a natural setting.", "Sanatoriy va sog'lomlashtirish xizmatlari; tabiatda sayr; mahalliy taomlar; uzoq muddatli dam olish", "Санаторно-оздоровительные услуги; прогулки на природе; местная кухня; длительный отдых", "Sanatorium and wellness services; walks in nature; local cuisine; longer stays", "41.1097151, 71.8044818"),
    ("Farg'ona", "M.Topvoldiyev", "M.Topvoldiyev turizm mahallasi Farg'ona viloyatida joylashgan bo'lib, xalqaro kulolchilik markazi, Xo'ja Rushnoiy ziyoratgohi va kulollar galereyalari bilan mashhur.", "Туристическая махалля им. М. Топволдиева в Ферганской области известна международным центром керамики, мазаром Ходжа Рушноий и галереями гончаров.", "M. Topvoldiyev Tourism Mahalla in Fergana Region is known for its international pottery centre, the Khoja Rushnoiy shrine and potters' galleries.", "Kulolchilik ustaxonalarida mahorat darslari; galereyalarni ko'rish; ziyorat; gastronomik master-klasslar", "Мастер-классы в гончарных мастерских; посещение галерей; паломничество; гастрономические мастер-классы", "Pottery masterclasses; visiting galleries; pilgrimage; gastronomic masterclasses", "40.364293, 71.277335"),
]


def _normalize(name: str) -> str:
    """Normalize a name for fuzzy matching."""
    s = name.lower().strip()
    for suffix in ["turizm qishlog'i", "turizm mahallasi", "etno turizm qishlog'i"]:
        s = s.replace(suffix, "")
    s = s.strip()
    s = re.sub(r"[^a-z0-9\u0400-\u04ff\u00e0-\u024f'ʼ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_location(loc_str: str):
    """Parse location string into (lat, lng) or (None, None)."""
    if not loc_str or not isinstance(loc_str, str):
        return None, None

    decimal_match = re.match(
        r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$", loc_str
    )
    if decimal_match:
        lat, lng = float(decimal_match.group(1)), float(decimal_match.group(2))
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng

    return None, None


def _convert_to_jpg(image_path: Path) -> tuple[bytes, str]:
    """Read an image file and return (jpeg_bytes, filename.jpg)."""
    img = Image.open(image_path)
    img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    new_name = image_path.stem + ".jpg"
    return buf.getvalue(), new_name


def _find_village_folder(region_dir: Path, village_name: str):
    """Find the best matching subdirectory for a village name."""
    if not region_dir.is_dir():
        return None

    target = _normalize(village_name)
    best_match = None
    best_score = 0

    for sub in region_dir.iterdir():
        if not sub.is_dir():
            continue
        folder_norm = _normalize(sub.name)

        if folder_norm == target:
            return sub

        if target in folder_norm or folder_norm in target:
            score = len(folder_norm) + len(target)
            if score > best_score:
                best_score = score
                best_match = sub

    return best_match


def _get_image_files(folder: Path) -> list[Path]:
    """Collect all image files from a folder, sorted by name."""
    if not folder or not folder.is_dir():
        return []
    return sorted(
        f
        for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )


class Command(BaseCommand):
    help = "Import tourism villages data and images from mat/ folder"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mat",
            default=str(settings.BASE_DIR / "mat"),
            help="Path to the mat/ folder with images",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing City, Village, Gallery data before importing",
        )

    def handle(self, *args, **options):
        mat_path = Path(options["mat"])

        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            Gallery.objects.all().delete()
            Village.objects.all().delete()
            City.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("  Flushed."))

        # ── Step 1: Create 12 regions ───────────────────────────────
        self.stdout.write("\n── Creating 12 regions ──")
        city_map = {}
        for idx, region_name in enumerate(ALL_REGIONS, start=1):
            city, created = City.objects.get_or_create(
                name_uz=region_name,
                defaults={"name": region_name, "order": idx},
            )
            city_map[region_name] = city
            status = "CREATED" if created else "EXISTS"
            self.stdout.write(f"  [{status}] {region_name} (id={city.pk})")

        # ── Step 2: Import villages from embedded data ──────────────
        self.stdout.write("\n── Importing villages ──")
        village_count = 0
        gallery_count = 0

        for row_idx, row in enumerate(VILLAGES_DATA, start=1):
            region, village_name, desc_uz, desc_ru, desc_en, act_uz, act_ru, act_en, location = row

            # Parse activities into structured list
            activities = []
            act_uz_list = [a.strip() for a in act_uz.split(";") if a.strip()]
            act_ru_list = [a.strip() for a in act_ru.split(";") if a.strip()]
            act_en_list = [a.strip() for a in act_en.split(";") if a.strip()]
            max_len = max(len(act_uz_list), len(act_ru_list), len(act_en_list))
            for i in range(max_len):
                activities.append({
                    "uz": act_uz_list[i] if i < len(act_uz_list) else "",
                    "ru": act_ru_list[i] if i < len(act_ru_list) else "",
                    "en": act_en_list[i] if i < len(act_en_list) else "",
                })

            lat, lng = _parse_location(location)

            city = city_map.get(region)
            if not city:
                self.stderr.write(self.style.WARNING(
                    f"  Row {row_idx}: Unknown region '{region}', skipping."
                ))
                continue

            village, created = Village.objects.get_or_create(
                name_uz=village_name,
                city=city,
                defaults={
                    "name": village_name,
                    "description_uz": desc_uz,
                    "description_ru": desc_ru,
                    "description_en": desc_en,
                    "latitude": lat,
                    "longitude": lng,
                    "activities": activities,
                    "order": row_idx,
                },
            )

            if not created:
                village.description_uz = desc_uz
                village.description_ru = desc_ru
                village.description_en = desc_en
                village.latitude = lat
                village.longitude = lng
                village.activities = activities
                village.save()

            village_count += 1
            status = "CREATED" if created else "UPDATED"
            self.stdout.write(f"  [{status}] {region} → {village_name}")

            # ── Step 3: Import images ───────────────────────────────
            region_folder_name = REGION_FOLDER_MAP.get(region)
            if not region_folder_name:
                continue

            region_dir = mat_path / region_folder_name
            village_folder = _find_village_folder(region_dir, village_name)
            images = _get_image_files(village_folder)

            if not images:
                self.stdout.write(
                    self.style.WARNING(f"    No images found for '{village_name}'")
                )
                continue

            # Clear existing gallery to avoid duplicates on re-run
            old_gallery_count = village.gallery.count()
            if old_gallery_count:
                village.gallery.all().delete()
                self.stdout.write(f"    Cleared {old_gallery_count} old gallery images")

            for img_idx, img_path in enumerate(images):
                try:
                    jpg_bytes, jpg_name = _convert_to_jpg(img_path)
                    content = ContentFile(jpg_bytes, name=jpg_name)

                    if img_idx == 0 and not village.image:
                        village.image.save(jpg_name, content, save=True)
                        self.stdout.write(f"    → Main image: {img_path.name}")
                    else:
                        Gallery.objects.create(
                            village=village,
                            image=content,
                            name=img_path.stem,
                            order=img_idx,
                        )
                        gallery_count += 1
                        self.stdout.write(f"    → Gallery #{img_idx}: {img_path.name}")

                except Exception as e:
                    self.stderr.write(self.style.ERROR(
                        f"    ✗ Error processing {img_path.name}: {e}"
                    ))

        # ── Summary ─────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(
            f"Done! Cities: {City.objects.count()}, "
            f"Villages: {village_count}, "
            f"Gallery images: {gallery_count}"
        ))
