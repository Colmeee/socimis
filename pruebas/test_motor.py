"""El motor (puntuacion), el modelo, el vínculo vasco, la base SQLite y la puerta robots.txt, con fichas sintéticas."""
import os
import sqlite3
import tempfile
import unittest

from socimis import base, modelo, puntuacion, robots, vinculo_vasco

HOY = "2026-10-26"
URL = "https://ejemplo.invalid/doc.pdf"


def ficha_ejemplo():
    f = modelo.ficha_vacia()
    f["sociedad"].update({"nombre": "EJEMPLO PATRIMONIAL SOCIMI, S.A.", "nif": "A00000000", "segmento": "BME Growth", "mercado": "BME MTF Equity",
                          "capitalizacion": 216000000.0, "cotizacion": 14.6, "fecha_incorporacion": "2020-10-14", "url_ficha": "https://ejemplo.invalid/ficha"})
    d = lambda v, **k: modelo.dato(v, URL, fecha="2025-12-31", huella="abc", consultado=HOY, **k)
    for campo, v in {"tesoreria": 13217301.0, "valor_razonable_inmuebles": 363437000.0, "prestamos_lp": 117385551.0, "prestamos_cp": 6483865.0,
                     "ingresos_rentas": 9832863.0, "patrimonio_neto": 259382688.0, "dividendos_pagados": 2245589.0, "gav_valoracion": 363437000.0}.items():
        modelo.poner(f, "2025", campo, d(v))
    modelo.poner(f, "2025", "dividendo_acordado", d(3226792.91))
    modelo.poner(f, "2025", "ltv_declarado", d(31.8, unidad="%"))
    modelo.poner(f, "2024", "dividendo_acordado", d(2245589.0))
    f["accionistas"] = [{"accionista": "Cartera Ficticia Uno, S.L.", "tipo": "juridica", "pct_total": 5.73, "fuente": URL},
                        {"accionista": "D. Nombre Inventado", "tipo": "fisica", "pct_total": 5.73, "a_traves_de": "Cartera Ficticia Uno, S.L.", "fuente": URL},
                        {"accionista": "Holding Ficticio Tres, S.L.U.", "tipo": "juridica", "pct_total": 5.01, "fuente": URL}]
    f["vencimientos"] = [{"entidad": "Banco Ejemplo", "importe": 21872301.0, "vencimiento": "2031-09-05", "fuente": URL},
                         {"entidad": "Kutxabank", "importe": 1967616.0, "vencimiento": "2036-04-21", "fuente": URL},
                         {"entidad": "Banco Ejemplo", "importe": 193330.0, "vencimiento": "2026-09-10", "fuente": URL}]
    f["activos"] = [{"nombre": "Aparthotel Gasteiz", "ubicacion": "Avenida de Gasteiz 45, Vitoria", "valor": 34800000.0, "fuente": URL},
                    {"nombre": "Edificio Valencia", "ubicacion": "Avenida del Oeste 48, Valencia", "valor": 60700000.0, "fuente": URL},
                    {"nombre": "Edificio Bilbao Ledesma", "ubicacion": "Calle Ledesma 5, Bilbao", "valor": 15000000.0, "fuente": URL}]
    f["documentos"] = [{"tipo": "cuentas_anuales", "fecha": "2026-05-21", "url": URL, "huella": "abc"}, {"tipo": "semestral", "fecha": "2025-10-31", "url": URL, "huella": "def"}]
    return f


class TestCriterios(unittest.TestCase):
    def test_cuadran(self):
        c = puntuacion.cargar_criterios()
        self.assertEqual(sum(c[d]["peso"] for d in puntuacion.ORDEN), 100)

    def test_un_peso_mal_revienta(self):
        c = puntuacion.cargar_criterios()
        c["madurez"]["peso"] = 11
        with self.assertRaises(puntuacion.CriteriosInvalidos):
            puntuacion.validar(c)


class TestMotor(unittest.TestCase):
    def setUp(self):
        self.c = puntuacion.cargar_criterios()
        self.f = ficha_ejemplo()
        modelo.completar_derivados(self.f)
        self.ev = puntuacion.evaluar(self.f, self.c, HOY)

    def test_derivados_con_formula(self):
        e = self.f["ejercicios"]["2025"]
        self.assertEqual(e["deuda_financiera"]["valor"], 123869416.0)
        self.assertEqual(e["deuda_financiera"]["contraste"], "derivado")
        self.assertEqual(e["deuda_financiera_neta"]["valor"], 110652115.0)
        self.assertEqual(e["ltv_neto"]["valor"], 30.4)
        self.assertIn("GAV", e["ltv_neto"]["nota"])

    def test_cobertura_completa_y_tramo(self):
        self.assertEqual(self.ev["cobertura"], 6)
        self.assertIsNotNone(self.ev["puntos"])
        self.assertIn(self.ev["tramo"], ("prioritaria", "interesante", "de momento no"))
        self.assertEqual(sum(d["max"] for d in self.ev["dimensiones"]), 100)
        self.assertLessEqual(self.ev["puntos"], 100)

    def test_ltv_declarado_manda_y_tiene_por_que(self):
        ap = self.ev["dimensiones"][0]
        self.assertEqual(ap["id"], "apalancamiento")
        ltv = ap["partes"][0]
        self.assertIn("31,8", ltv["detalle"])
        self.assertIn("declarado", ltv["detalle"])
        self.assertEqual(ltv["fuente"], URL)
        self.assertAlmostEqual(ltv["puntos"], 17 * (60 - 31.8) / 30, places=1)

    def test_vencimientos_a_dos_anios(self):
        v = self.ev["dimensiones"][0]["partes"][1]
        self.assertEqual(v["estado"], "cumplida")           # solo 193.330 € (0,8 %) vence antes de 2028-10-26
        self.assertIn("2028-10-26", v["detalle"])

    def test_dividendos(self):
        dv = {p["etiqueta"]: p for p in self.ev["dimensiones"][1]["partes"]}
        self.assertEqual(dv["Reparte dividendo"]["estado"], "cumplida")
        self.assertEqual(dv["Crece"]["estado"], "cumplida")
        self.assertIn("1,5 %", dv["Rendimiento sobre capitalización"]["detalle"])

    def test_concentracion_no_cuenta_dos_veces_a_la_persona_fisica(self):
        cc = {p["etiqueta"]: p for p in self.ev["dimensiones"][3]["partes"]}
        self.assertIn("2 accionistas", cc["Suma de significativos"]["detalle"])
        self.assertEqual(cc["Persona física detrás"]["estado"], "cumplida")

    def test_sin_datos_no_resta(self):
        f = modelo.ficha_vacia()
        f["sociedad"]["nombre"] = "VACÍA"
        ev = puntuacion.evaluar(f, self.c, HOY)
        self.assertEqual(ev["cobertura"], 0)
        self.assertIsNone(ev["puntos"])
        self.assertEqual(ev["tramo"], "sin datos")
        self.assertTrue(all(d["estado"] == "sin datos" for d in ev["dimensiones"]))
        self.assertTrue(ev["avisos"])

    def test_determinista(self):
        self.assertEqual(puntuacion.evaluar(self.f, self.c, HOY), self.ev)

    def test_texto(self):
        t = puntuacion.texto(self.ev, self.f)
        self.assertIn("EJEMPLO PATRIMONIAL SOCIMI", t)
        self.assertIn("fuente: " + URL, t)


class TestModelo(unittest.TestCase):
    def test_contraste_desconocido(self):
        with self.assertRaises(ValueError):
            modelo.dato(1, URL, contraste="rumor")

    def test_campo_desconocido(self):
        with self.assertRaises(KeyError):
            modelo.poner(modelo.ficha_vacia(), "2025", "caja_oculta", modelo.dato(1, URL))

    def test_no_consta_es_un_valor(self):
        d = modelo.no_consta("no publica NAV")
        self.assertIsNone(d["valor"])
        self.assertEqual(d["contraste"], "no_consta")


class TestVinculoVasco(unittest.TestCase):
    def test_fuerte_por_activos_y_financiacion(self):
        f = ficha_ejemplo()
        v = vinculo_vasco.evaluar(f, {"cuentas": "Préstamo con garantía hipotecaria con Caja Laboral Popular del inmueble de Vitoria.\nOtra línea sin nada."})
        self.assertEqual(v["grado"], "fuerte")
        self.assertEqual(len(v["activos"]), 2)
        self.assertEqual(set(v["provincias"]), {"Álava", "Bizkaia"})
        self.assertEqual(v["pct_valor_en_pais_vasco"], 45.1)
        self.assertEqual([x["entidad"] for x in v["financiacion"]], ["Kutxabank"])
        self.assertEqual(v["menciones"][0]["provincia"], "Álava")

    def test_ninguno(self):
        f = modelo.ficha_vacia()
        self.assertEqual(vinculo_vasco.evaluar(f, {"x": "Un edificio en Valencia y otro en Sevilla."})["grado"], "ninguno")

    def test_indicio_sin_falsos_positivos_dentro_de_palabras(self):
        f = modelo.ficha_vacia()
        v = vinculo_vasco.evaluar(f, {"x": "Alava es parte de la palabra lavalavava? no: 'Durango' sí es un lugar."})
        self.assertEqual(v["grado"], "indicio")
        self.assertEqual(v["menciones"][0]["lugar"], "Alava")


class TestVinculoVascoExclusiones(unittest.TestCase):
    def test_bbva_calles_y_apellidos_no_cuentan(self):
        f = modelo.ficha_vacia()
        textos = {"x": "Préstamo con Banco Bilbao Vizcaya Argentaria S.A. 27.000\ndomicilio en Calle Príncipe de Vergara 112, Madrid\n"
                       "Edificio Navas de Tolosa 279, Barcelona\nC/ SAN SEBASTIAN 25 ALCANTARILLA (MURCIA)\nDon Fernando Lacadena Azpeitia: consejero\n"}
        self.assertEqual(vinculo_vasco.evaluar(f, textos)["grado"], "ninguno")

    def test_lugares_de_verdad_siguen_contando(self):
        f = modelo.ficha_vacia()
        v = vinculo_vasco.evaluar(f, {"x": "Locales en el Parque Comercial de Txingudi, en Irún\nOtaola Hiribidea 2 Eibar 6.228.332\nCalle Arrasate 27, San Sebastián\n"})
        self.assertEqual(v["grado"], "indicio")
        lugares = {m["lugar"] for m in v["menciones"]}
        self.assertTrue({"Eibar", "Irún"} <= lugares)
        self.assertTrue(lugares & {"Arrasate", "San Sebastián"})       # la calle Arrasate de Donostia: cualquiera de los dos vale
        self.assertEqual(len(v["menciones"]), 3)


class TestBase(unittest.TestCase):
    def test_sqlite_y_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            fichas = os.path.join(tmp, "fichas")
            os.makedirs(fichas)
            f = ficha_ejemplo()
            modelo.completar_derivados(f)
            f["vinculo_vasco"] = vinculo_vasco.evaluar(f, {})
            modelo.guardar(f, os.path.join(fichas, "A00000000.json"))
            c = puntuacion.cargar_criterios()
            n = base.construir(fichas, os.path.join(tmp, "b.sqlite"), os.path.join(tmp, "csv"), {"A00000000": (HOY, puntuacion.evaluar(f, c, HOY))})
            self.assertEqual(n, 1)
            con = sqlite3.connect(os.path.join(tmp, "b.sqlite"))
            self.assertEqual(con.execute("SELECT valor, contraste FROM dato WHERE campo='ltv_neto'").fetchone(), (30.4, "derivado"))
            self.assertEqual(con.execute("SELECT count(*) FROM accionista").fetchone()[0], 3)
            self.assertEqual(con.execute("SELECT grado, n_activos FROM vinculo_vasco").fetchone(), ("fuerte", 2))
            self.assertEqual(con.execute("SELECT count(*) FROM puntuacion").fetchone()[0], 6)
            self.assertEqual(con.execute("SELECT fuente FROM dato WHERE campo='tesoreria'").fetchone()[0], URL)
            self.assertTrue(os.path.exists(os.path.join(tmp, "csv", "dato.csv")))
            with open(os.path.join(tmp, "csv", "sociedad.csv"), encoding="utf-8") as fh:
                self.assertIn("A00000000", fh.read())


class TestCortesia(unittest.TestCase):
    def test_la_excepcion_de_bme_es_explicita_y_unica(self):
        from socimis import cortesia
        self.assertEqual(list(cortesia.EXCEPCIONES_ROBOTS), ["apiweb.bolsasymercados.es"])
        self.assertIn("decisión de Juan", cortesia.EXCEPCIONES_ROBOTS["apiweb.bolsasymercados.es"])

    def test_lista_blanca_y_destino_dentro(self):
        from socimis import cortesia
        os.environ["SOCIMIS_SIN_RED"] = "1"
        with tempfile.TemporaryDirectory() as tmp:
            cola = cortesia.Cola(tmp, hoy=HOY)
            with self.assertRaises(cortesia.Rechazada):
                cola.bajar("https://169.254.169.254/latest/meta-data", "x.pdf")
            with self.assertRaises(cortesia.Rechazada):
                cola.bajar("http://www.cnmv.es/x.pdf", "x.pdf")

    def test_sin_red_no_baja_y_reanuda_desde_el_diario(self):
        import json
        from socimis import cortesia
        os.environ["SOCIMIS_SIN_RED"] = "1"
        with tempfile.TemporaryDirectory() as tmp:
            cola = cortesia.Cola(tmp, hoy=HOY)
            with self.assertRaises(RuntimeError):
                cola.bajar("https://www.cnmv.es/x.pdf", "x.pdf")
            # una línea en el diario con su fichero en disco se da por hecha sin tocar la red
            with open(os.path.join(tmp, "y.pdf"), "wb") as f:
                f.write(b"%PDF")
            with open(cola.diario, "a", encoding="utf-8") as f:
                f.write(json.dumps({"url": "https://apiweb.bolsasymercados.es/y.pdf", "fichero": "y.pdf", "huella": "h", "bytes": 4, "fecha": HOY}) + "\n")
            cola2 = cortesia.Cola(tmp, hoy=HOY)
            self.assertEqual(cola2.bajar("https://apiweb.bolsasymercados.es/y.pdf", "y.pdf")["huella"], "h")


class TestEscaneado(unittest.TestCase):
    def test_mitad_de_paginas_vacias(self):
        from socimis import texto_pdf
        lleno = "x" * 500
        self.assertFalse(texto_pdf.es_escaneado("\f".join([lleno] * 10) + "\f"))
        self.assertTrue(texto_pdf.es_escaneado("\f".join([lleno] * 4 + [""] * 47) + "\f"))      # Arrienda: 4 páginas con texto de 51
        self.assertTrue(texto_pdf.es_escaneado(""))


class TestRobots(unittest.TestCase):
    def test_reglas(self):
        txt = "User-agent: *\nDisallow: /privado\nAllow: /privado/publico\n\nUser-agent: socimis\nDisallow: /solo-para-nosotros\n"
        self.assertTrue(robots.permitido(txt, "socimis", "/docs/x.pdf"))
        self.assertFalse(robots.permitido(txt, "socimis", "/solo-para-nosotros/x"))
        self.assertFalse(robots.permitido(txt, "*", "/privado/otro"))
        self.assertTrue(robots.permitido(txt, "*", "/privado/publico/x"))

    def test_bom_y_lineas_en_blanco(self):
        txt = "﻿User-agent: *\n\nDisallow: /\n"
        self.assertFalse(robots.permitido(txt, "socimis", "/cualquier"))

    def test_cuerpo_que_no_es_robots(self):
        self.assertFalse(robots.es_robots("<html><body>Not found</body></html>"))
        self.assertTrue(robots.es_robots(""))
        self.assertTrue(robots.es_robots("User-agent: *\nAllow: /"))

    def test_regla_ilegible(self):
        self.assertTrue(robots.regla_ilegible("Disallow: /caf�\n"))
        self.assertFalse(robots.regla_ilegible("# comentario �\nAllow: /"))

    def test_comodines_y_porcentajes(self):
        self.assertFalse(robots.permitido("User-agent: *\nDisallow: /*?date=\n", "x", "/a/b?date=1"))
        self.assertFalse(robots.permitido("User-agent: *\nDisallow: /foo%20bar\n", "x", "/foo bar"))
        self.assertFalse(robots.permitido("User-agent: *\nDisallow: /*.shtml$\n", "x", "/p/a.shtml"))
        self.assertTrue(robots.permitido("User-agent: *\nDisallow: /*.shtml$\n", "x", "/p/a.shtml?x"))

    def test_nombre_agente(self):
        self.assertEqual(robots.nombre_agente("socimis/0.1 (+uso propio)"), "socimis")


if __name__ == "__main__":
    unittest.main()


class TestClave(unittest.TestCase):
    def test_nif_o_isin(self):
        from socimis import modelo
        self.assertEqual(modelo.clave_valida("a-87.934.741"), "A87934741")
        self.assertEqual(modelo.clave_valida("ES0105746004"), "ES0105746004")
        self.assertIsNone(modelo.clave_valida("../x"))
        self.assertEqual(modelo.clave({"sociedad": {"nif": "A87934741", "isin": "ES0105746004"}}), "A87934741")
        self.assertEqual(modelo.clave({"sociedad": {"nif": None, "isin": "ES0105746004"}}), "ES0105746004")
        self.assertIsNone(modelo.clave({"sociedad": {}}))


class TestGeo(unittest.TestCase):
    def test_provincias(self):
        from socimis import geo
        casos = {"Avenida de Gasteiz 45, Vitoria": "Álava", "Avenida del Oeste 48, Valencia": "Valencia", "Paseo Heriz 38, San Sebastián": "Gipuzkoa",
                 "Calle Valencia 23, 28012 Madrid": "Madrid", "Calle Bilbao 3, Madrid": "Madrid", "San Sebastián de los Reyes": "Madrid",
                 "Nave logística en Illescas (Toledo)": "Toledo", "Hotel en Playa de Palma": "Illes Balears", "Plaza Yamaguchi 12, Pamplona": "Navarra",
                 "-": None, "28.949.620": None, "": None, None: None, "Oficinas en Lisboa": None,
                 "Calle Sancho de Ávila nº 32-34": None, "Calle Granada 76, Málaga": "Málaga", "Carrer de València 200, Barcelona": "Barcelona",
                 "Calle Vitoria Gasteiz 6. Bilbao": "Bizkaia", "Oficinas Castellana 200": "Madrid"}
        for texto, esperado in casos.items():
            self.assertEqual(geo.provincia_de_lugar(texto), esperado, texto)
        self.assertEqual(geo.provincia_de_activo({"nombre": "Edificio Barcelona Sancho de Ávila", "ubicacion": "Calle Sancho de Ávila nº 32-34"}), "Barcelona")
        self.assertEqual(geo.provincia_de_activo({"nombre": "Apartamentos Málaga Granada 76", "ubicacion": None}), "Málaga")
        self.assertEqual(geo.comunidad("Álava"), "País Vasco")
        self.assertEqual(geo.comunidad("Toledo"), "Castilla-La Mancha")
        self.assertIsNone(geo.comunidad("Lisboa"))
