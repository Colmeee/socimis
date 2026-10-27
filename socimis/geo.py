"""Dónde está un inmueble: la provincia (y la comunidad) a partir del texto de ubicación que publica la sociedad.

Por qué existe: el piloto vasco midió el vínculo con un gazetteer de tres provincias (`vasco.json`); para el resto de
España hace falta lo mismo a escala nacional, al menos a nivel de provincia. Aquí hay un gazetteer corto —las 52 provincias
con sus nombres cooficiales, sus capitales y los municipios de más de 50.000 habitantes, más algunos sitios de inmuebles
corrientes (polígonos, playas)— y una función que devuelve la provincia de una ubicación o None. Es deliberadamente
conservador: un nombre que falte no se detecta (se amplía el diccionario), y nunca se inventa. Reutiliza el gazetteer vasco
para Álava, Bizkaia y Gipuzkoa, que es más fino.
"""
import re
from pathlib import Path

from . import vinculo_vasco

AQUI = Path(__file__).resolve().parent

# provincia -> comunidad autónoma
COMUNIDADES = {
    "Madrid": "Madrid", "Barcelona": "Cataluña", "Girona": "Cataluña", "Lleida": "Cataluña", "Tarragona": "Cataluña",
    "Valencia": "Comunidad Valenciana", "Alicante": "Comunidad Valenciana", "Castellón": "Comunidad Valenciana",
    "Sevilla": "Andalucía", "Málaga": "Andalucía", "Cádiz": "Andalucía", "Córdoba": "Andalucía", "Granada": "Andalucía", "Huelva": "Andalucía", "Jaén": "Andalucía", "Almería": "Andalucía",
    "Álava": "País Vasco", "Bizkaia": "País Vasco", "Gipuzkoa": "País Vasco",
    "Illes Balears": "Illes Balears", "Las Palmas": "Canarias", "Santa Cruz de Tenerife": "Canarias",
    "Zaragoza": "Aragón", "Huesca": "Aragón", "Teruel": "Aragón", "Navarra": "Navarra", "La Rioja": "La Rioja", "Murcia": "Región de Murcia",
    "Asturias": "Asturias", "Cantabria": "Cantabria", "A Coruña": "Galicia", "Lugo": "Galicia", "Ourense": "Galicia", "Pontevedra": "Galicia",
    "Valladolid": "Castilla y León", "Burgos": "Castilla y León", "León": "Castilla y León", "Salamanca": "Castilla y León", "Palencia": "Castilla y León",
    "Zamora": "Castilla y León", "Ávila": "Castilla y León", "Segovia": "Castilla y León", "Soria": "Castilla y León",
    "Toledo": "Castilla-La Mancha", "Ciudad Real": "Castilla-La Mancha", "Albacete": "Castilla-La Mancha", "Cuenca": "Castilla-La Mancha", "Guadalajara": "Castilla-La Mancha",
    "Badajoz": "Extremadura", "Cáceres": "Extremadura", "Ceuta": "Ceuta", "Melilla": "Melilla",
}

# provincia -> nombres que la delatan (la propia provincia, la capital, municipios grandes). Sin los tres vascos: vienen de vasco.json.
LUGARES = {
    "Madrid": ["Madrid", "Alcalá de Henares", "Alcobendas", "Alcorcón", "Aranjuez", "Arganda del Rey", "Boadilla del Monte", "Collado Villalba", "Colmenar Viejo", "Coslada", "Fuenlabrada", "Getafe", "Las Rozas", "Leganés", "Majadahonda", "Móstoles", "Parla", "Pinto", "Pozuelo de Alarcón", "Rivas-Vaciamadrid", "Rivas Vaciamadrid", "San Fernando de Henares", "San Sebastián de los Reyes", "Torrejón de Ardoz", "Tres Cantos", "Valdemoro", "Villaviciosa de Odón", "Alcalá de Henares", "Barajas", "Vallecas", "Chamartín", "Castellana", "Azca", "Las Tablas", "Méndez Álvaro"],
    "Barcelona": ["Barcelona", "Badalona", "Castelldefels", "Cerdanyola", "Cornellà", "Cornellá", "El Prat", "Esplugues", "Gavà", "Granollers", "L'Hospitalet", "Hospitalet", "Manresa", "Mataró", "Mollet", "Rubí", "Sabadell", "Sant Boi", "Sant Cugat", "Sant Feliu de Llobregat", "Santa Coloma de Gramenet", "Terrassa", "Viladecans", "Vilanova i la Geltrú", "Vic", "Sitges", "Martorell", "Igualada", "22@", "Poblenou", "Zona Franca", "Eixample", "Sant Just Desvern"],
    "Girona": ["Girona", "Gerona", "Figueres", "Blanes", "Lloret de Mar", "Olot", "Salt", "Palafrugell", "Roses", "Platja d'Aro"],
    "Lleida": ["Lleida", "Lérida", "Balaguer", "Tàrrega"],
    "Tarragona": ["Tarragona", "Reus", "Cambrils", "Salou", "Tortosa", "Vila-seca", "El Vendrell", "Valls"],
    "Valencia": ["Valencia", "València", "Torrent", "Gandia", "Gandía", "Paterna", "Sagunto", "Sagunt", "Alzira", "Mislata", "Burjassot", "Ontinyent", "Xàtiva", "Manises", "Ribarroja", "Riba-roja", "Quart de Poblet", "Aldaia", "Alboraya", "Alboraia", "Cullera"],
    "Alicante": ["Alicante", "Alacant", "Elche", "Elx", "Torrevieja", "Orihuela", "Benidorm", "Alcoy", "Alcoi", "San Vicente del Raspeig", "Elda", "Dénia", "Denia", "Petrer", "Villena", "Calpe", "Calp", "Jávea", "Xàbia", "Altea", "Santa Pola", "Villajoyosa", "Pilar de la Horadada"],
    "Castellón": ["Castellón", "Castelló", "Vila-real", "Villarreal", "Burriana", "Borriana", "Vinaròs", "Vinaroz", "Benicarló", "Onda", "Peñíscola", "Oropesa del Mar", "Almassora"],
    "Sevilla": ["Sevilla", "Dos Hermanas", "Alcalá de Guadaíra", "Utrera", "Mairena del Aljarafe", "Écija", "Ecija", "La Rinconada", "Los Palacios", "Carmona", "Camas", "Tomares", "Bormujos", "Lebrija"],
    "Málaga": ["Málaga", "Malaga", "Marbella", "Mijas", "Vélez-Málaga", "Velez-Malaga", "Fuengirola", "Torremolinos", "Benalmádena", "Benalmadena", "Estepona", "Rincón de la Victoria", "Antequera", "Alhaurín de la Torre", "Ronda", "Nerja", "Torrox", "Manilva", "Puerto Banús"],
    "Cádiz": ["Cádiz", "Cadiz", "Jerez", "Algeciras", "San Fernando", "El Puerto de Santa María", "Chiclana", "Sanlúcar de Barrameda", "La Línea", "Puerto Real", "Rota", "Tarifa", "Sotogrande"],
    "Córdoba": ["Córdoba", "Cordoba", "Lucena", "Puente Genil", "Montilla", "Priego de Córdoba"],
    "Granada": ["Granada", "Motril", "Almuñécar", "Armilla", "Baza", "Loja", "Maracena"],
    "Huelva": ["Huelva", "Lepe", "Almonte", "Isla Cristina", "Ayamonte", "Moguer", "Punta Umbría"],
    "Jaén": ["Jaén", "Jaen", "Linares", "Úbeda", "Ubeda", "Andújar", "Martos", "Alcalá la Real"],
    "Almería": ["Almería", "Almeria", "Roquetas de Mar", "El Ejido", "Níjar", "Nijar", "Vera", "Adra", "Huércal-Overa", "Mojácar", "Vícar"],
    "Illes Balears": ["Illes Balears", "Islas Baleares", "Baleares", "Mallorca", "Palma", "Palma de Mallorca", "Calvià", "Calvia", "Ibiza", "Eivissa", "Menorca", "Manacor", "Marratxí", "Llucmajor", "Inca", "Santa Eulària", "Sant Antoni de Portmany", "Alcúdia", "Alcudia", "Mahón", "Maó", "Ciutadella", "Formentera", "Magaluf", "Playa de Palma", "Santa Ponsa", "Andratx", "Sóller", "Pollença", "Pollensa"],
    "Las Palmas": ["Las Palmas", "Las Palmas de Gran Canaria", "Gran Canaria", "Lanzarote", "Fuerteventura", "Telde", "Santa Lucía de Tirajana", "San Bartolomé de Tirajana", "Arrecife", "Arucas", "Agüimes", "Puerto del Rosario", "Maspalomas", "Playa del Inglés", "Mogán", "Corralejo", "Puerto del Carmen", "Yaiza", "Tías"],
    "Santa Cruz de Tenerife": ["Santa Cruz de Tenerife", "Tenerife", "La Laguna", "San Cristóbal de La Laguna", "Arona", "Adeje", "Granadilla de Abona", "La Orotava", "Los Realejos", "Puerto de la Cruz", "La Palma", "La Gomera", "El Hierro", "Costa Adeje", "Playa de las Américas", "Los Cristianos"],
    "Zaragoza": ["Zaragoza", "Calatayud", "Utebo", "Ejea de los Caballeros", "Plaza Zaragoza", "Plataforma Logística de Zaragoza"],
    "Huesca": ["Huesca", "Barbastro", "Monzón", "Jaca", "Fraga", "Formigal", "Cerler"],
    "Teruel": ["Teruel", "Alcañiz"],
    "Navarra": ["Navarra", "Nafarroa", "Pamplona", "Iruña", "Iruñea", "Tudela", "Barañáin", "Burlada", "Estella", "Zizur", "Tafalla", "Noáin"],
    "La Rioja": ["La Rioja", "Logroño", "Calahorra", "Arnedo", "Haro"],
    "Murcia": ["Murcia", "Cartagena", "Lorca", "Molina de Segura", "Alcantarilla", "Mazarrón", "Cieza", "Yecla", "Águilas", "Torre-Pacheco", "San Javier", "Los Alcázares", "La Manga", "Caravaca", "Jumilla", "Totana"],
    "Asturias": ["Asturias", "Oviedo", "Gijón", "Gijon", "Avilés", "Aviles", "Siero", "Langreo", "Mieres", "Llanera", "Castrillón"],
    "Cantabria": ["Cantabria", "Santander", "Torrelavega", "Castro Urdiales", "Camargo", "Piélagos", "Laredo", "Santoña", "El Astillero"],
    "A Coruña": ["A Coruña", "La Coruña", "Coruña", "Santiago de Compostela", "Ferrol", "Oleiros", "Narón", "Culleredo", "Arteixo", "Carballo", "Ribeira"],
    "Lugo": ["Lugo", "Monforte de Lemos", "Viveiro"],
    "Ourense": ["Ourense", "Orense", "Verín", "O Barco"],
    "Pontevedra": ["Pontevedra", "Vigo", "Vilagarcía", "Redondela", "Cangas", "Marín", "Ponteareas", "Lalín", "O Porriño", "Sanxenxo", "Mos"],
    "Valladolid": ["Valladolid", "Medina del Campo", "Laguna de Duero", "Arroyo de la Encomienda"],
    "Burgos": ["Burgos", "Miranda de Ebro", "Aranda de Duero"],
    "León": ["León", "Ponferrada", "San Andrés del Rabanedo", "Astorga"],
    "Salamanca": ["Salamanca", "Béjar", "Ciudad Rodrigo", "Santa Marta de Tormes"],
    "Palencia": ["Palencia", "Aguilar de Campoo"],
    "Zamora": ["Zamora", "Benavente", "Toro"],
    "Ávila": ["Ávila", "Avila", "Arévalo"],
    "Segovia": ["Segovia", "Cuéllar", "El Espinar"],
    "Soria": ["Soria", "Almazán"],
    "Toledo": ["Toledo", "Talavera de la Reina", "Illescas", "Seseña", "Ocaña", "Torrijos", "Yuncos"],
    "Ciudad Real": ["Ciudad Real", "Puertollano", "Tomelloso", "Alcázar de San Juan", "Valdepeñas", "Manzanares", "Daimiel"],
    "Albacete": ["Albacete", "Hellín", "Villarrobledo", "Almansa", "La Roda"],
    "Cuenca": ["Cuenca", "Tarancón"],
    "Guadalajara": ["Guadalajara", "Azuqueca de Henares", "Alovera", "Cabanillas del Campo", "Marchamalo", "Torija", "Quer"],
    "Badajoz": ["Badajoz", "Mérida", "Merida", "Don Benito", "Almendralejo", "Villanueva de la Serena", "Zafra"],
    "Cáceres": ["Cáceres", "Caceres", "Plasencia", "Navalmoral de la Mata", "Coria"],
    "Ceuta": ["Ceuta"],
    "Melilla": ["Melilla"],
}

# Un tramo que empieza por «Calle», «Avenida», «Carrer»… es una vía, y una vía puede llevar nombre de ciudad («Calle Granada 76,
# Málaga», «Calle Sancho de Ávila 32», «Carrer de València»): esos tramos no sirven para ubicar. Se ubica con los demás tramos.
RE_CALLE = re.compile(r"^(?:Calle|C/|C\.|Cl\.?|Avda\.?|Avenida|Av\.?|Paseo|Pº|P\.º|Plaza|Pza\.?|Pl\.?|Ronda|Carretera|Ctra\.?|Camino|Traves[ií]a|Glorieta|"
                      r"Carrer|Avinguda|Passeig|Plaça|Rambla|R[úu]a|Praza|Kalea|Alameda|Gran V[ií]a|Bulevar|Boulevard|Urbanizaci[oó]n|Urb\.?|Pol[ií]gono|Pol\.?)\b", re.I)
RE_TRAMO = re.compile(r",|;|\.\s|\s[-–]\s|\(|\)")
# Frases donde un nombre de lugar no es un lugar: se quitan antes de buscar.
EXCLUSIONES = [r"Pr[ií]ncipe de Vergara", r"Navas de Tolosa", r"Banco Bilbao Vizcaya", r"BBVA"]
_SS_REYES = re.compile(r"San Sebasti[aá]n de los Reyes", re.I)


def _patron(nombres):
    return re.compile(r"(?<![\wáéíóúñ])(" + "|".join(re.escape(n) for n in sorted(set(nombres), key=len, reverse=True)) + r")(?![\wáéíóúñ])", re.I)


class Gazetteer:
    def __init__(self):
        self.lugares = {}
        for prov, nombres in LUGARES.items():
            for n in nombres:
                self.lugares[n.lower()] = prov
        for prov, nombres in vinculo_vasco.cargar_gazetteer()["provincias"].items():
            for n in nombres:
                self.lugares.setdefault(n.lower(), prov)
        self.patron = _patron(list(self.lugares))
        self.exclusiones = [re.compile(x, re.I) for x in EXCLUSIONES]

    def provincia(self, texto, primera=False):
        """La provincia de un texto de ubicación («Avenida de Gasteiz 45, Vitoria» -> Álava) o None.
        Reglas: un código postal decide; los tramos que son una vía («Calle Granada 76») no cuentan; entre los demás tramos gana
        la última mención («Nave en Illescas (Toledo)» -> Toledo), salvo `primera=True`, pensado para el NOMBRE de un activo
        («Edificio Barcelona Sancho de Ávila» -> Barcelona). Si solo hay vías, None: una calle con nombre de ciudad no ubica."""
        if not texto or not re.search(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{3}", texto):
            return None
        from .fuentes.bme import PROVINCIAS_CP
        m = re.search(r"(?<!\d)(\d{5})(?!\d)", texto)
        if m and m.group(1)[:2] in PROVINCIAS_CP:
            return PROVINCIAS_CP[m.group(1)[:2]]
        if _SS_REYES.search(texto):
            return "Madrid"
        limpio = texto
        for rx in self.exclusiones:
            limpio = rx.sub(" ", limpio)
        tramos = [t.strip() for t in RE_TRAMO.split(limpio) if t and t.strip()]
        utiles = [t for t in tramos if not RE_CALLE.match(t)]
        encontrados = [self.lugares[x.group(1).lower()] for t in utiles for x in self.patron.finditer(t)]
        if not encontrados:
            return None
        return encontrados[0] if primera else encontrados[-1]


_G = None


def provincia_de_lugar(texto, primera=False):
    global _G
    if _G is None:
        _G = Gazetteer()
    return _G.provincia(texto, primera)


def provincia_de_activo(activo):
    """La provincia de un inmueble: por su ubicación y, si no la tiene o no ubica, por su nombre (primera mención)."""
    return provincia_de_lugar(activo.get("ubicacion")) or provincia_de_lugar(activo.get("nombre"), primera=True)


def comunidad(provincia):
    return COMUNIDADES.get(provincia)
