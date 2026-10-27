"""Las fuentes (CNMV y BME) con páginas reales guardadas; sin red (SOCIMIS_SIN_RED=1 hace reventar cualquier intento)."""
import os
import unittest

from socimis import red
from socimis.fuentes import bme, cnmv

AQUI = os.path.dirname(os.path.abspath(__file__))


def fixture(nombre):
    with open(os.path.join(AQUI, "fixtures", nombre), encoding="utf-8") as f:
        return f.read()


class TestCNMV(unittest.TestCase):
    def test_informes_anuales(self):
        inf = cnmv.informes_anuales(fixture("cnmv-ifa-merlin.html"))
        self.assertEqual(len(inf), 12)
        u = inf[0]
        self.assertEqual((u["registro"], u["fecha_estados"], u["publicado"]), ("20913", "2025-12-31", "2026-02-26"))
        self.assertEqual(u["auditor"], "PRICEWATERHOUSECOOPERS AUDITORES, S.L.")
        self.assertTrue(u["url_consolidada"].startswith("https://www.cnmv.es/webservices/verdocumento/ver?e="))
        self.assertTrue(u["url_individual"].startswith("https://www.cnmv.es/webservices/verdocumento/ver?e="))
        self.assertNotEqual(u["url_consolidada"], u["url_individual"])
        self.assertTrue(u["url_zip"])
        self.assertIn("Favorable", u["opinion"])
        self.assertEqual(inf[-1]["fecha_estados"], "2014-12-31")

    def test_nombre_entidad(self):
        self.assertEqual(cnmv.nombre_entidad(fixture("cnmv-ifa-merlin.html")), "MERLIN PROPERTIES, SOCIMI, S.A.")

    def test_participaciones(self):
        p = cnmv.participaciones(fixture("cnmv-participaciones-merlin.html"))
        self.assertEqual(p["derechos_voto_total"], 620000000)
        self.assertEqual(p["fecha_modificacion"], "2026-03-26")
        self.assertEqual(p["publicado"], "2026-03-27")
        acc = {a["accionista"]: a for a in p["accionistas"]}
        self.assertEqual(acc["BANCO SANTANDER, S.A."]["pct_total"], 22.268)
        self.assertEqual(acc["BANCO SANTANDER, S.A."]["pct_directo"], 16.697)
        self.assertEqual(acc["BANCO SANTANDER, S.A."]["tipo"], "juridica")
        self.assertEqual(acc["BLACKROCK INC."]["pct_total_ab"], 4.632)
        self.assertEqual(acc["PERSONA FISICA FICTICIA, EJEMPLO"]["tipo"], "fisica")
        self.assertEqual(acc["BANCO SANTANDER, S.A."]["fecha_registro"], "2016-11-02")
        self.assertTrue(acc["BANCO SANTANDER, S.A."]["url_pdf"].startswith("https://www.cnmv.es/webservices/"))

    def test_enlace_notificaciones(self):
        html = '<li><a href="Notificaciones-Participaciones.aspx?qS={6385c6dd-c557-4bbf-ae20-b01e37e83662}">Notificaciones</a></li>'
        self.assertEqual(cnmv.enlace_notificaciones(html), "https://www.cnmv.es/portal/Consultas/derechosvoto/Notificaciones-Participaciones.aspx?qS={6385c6dd-c557-4bbf-ae20-b01e37e83662}")

    def test_sin_red_revienta(self):
        os.environ["SOCIMIS_SIN_RED"] = "1"
        with self.assertRaises(RuntimeError):
            red.pedir_bytes("https://www.cnmv.es/", red.UA)


class TestBME(unittest.TestCase):
    DOCS = [
        {"url": "https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/05/05495_OtraInfRelev_20260521.pdf", "categoria": "Informes financieros anuales y de auditoría", "titulo": "Información financiera del ejercicio 2025 (12 MB)"},
        {"url": "https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/04/05495_OtraInfRelev_20260429.pdf", "categoria": "Informes financieros anuales y de auditoría", "titulo": "Información financiera del ejercicio 2025 (5 MB)"},
        {"url": "https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/04/05495_OtraInfRelev_20260430.pdf", "categoria": "Informes financieros anuales y de auditoría", "titulo": "Valoración de activos a 31 de diciembre de 2025 (66 KB)"},
        {"url": "https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/04/05495_OtraInfRelev_20260429_1.pdf", "categoria": "Informes financieros anuales y de auditoría", "titulo": "Valoración de activos a 31 de diciembre de 2025 (64 KB)"},
        {"url": "https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/07/05495_OtraInfRelev_20260706.pdf", "categoria": "Participaciones significativas", "titulo": "Participaciones significativas a 30 de junio de 2026 (275 KB)"},
        {"url": "https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/01/05495_OtraInfRelev_20260108.pdf", "categoria": "Participaciones significativas", "titulo": "Participaciones significativas a 31 de diciembre de 2025 (201 KB)"},
        {"url": "https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/06/05495_OtraInfRelev_20260624.pdf", "categoria": "Otra información relevante", "titulo": "Distribución y pago de dividendos 2026 (125 KB)"},
        {"url": "https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2025/10/05495_OtraInfRelev_20251031.pdf", "categoria": "Informes financieros semestrales y de auditoría / revisiones limitadas", "titulo": "Información financiera del primer semestre de 2025 (1 MB)"},
        {"url": "https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/05/05495_OtraInfRelev_20260526.pdf", "categoria": "Otra información relevante", "titulo": "Participación en Foro MedCap 2026 (6 MB)"},
    ]

    def test_fecha_de_url(self):
        self.assertEqual(bme.fecha_de_url(self.DOCS[0]["url"]), "2026-05-21")
        self.assertEqual(bme.fecha_de_url(self.DOCS[3]["url"]), "2026-04-29")
        self.assertIsNone(bme.fecha_de_url("https://x/y.pdf"))

    def test_clasificar(self):
        self.assertEqual([bme.clasificar(d) for d in self.DOCS], ["cuentas_anuales", "cuentas_anuales", "valoracion", "valoracion", "participaciones", "participaciones", "dividendo", "semestral", "otro"])

    def test_elegir_el_mas_reciente_y_el_gordo(self):
        e = bme.elegir_documentos(self.DOCS)
        self.assertEqual(sorted(e), ["cuentas_anuales", "dividendo", "participaciones", "semestral", "valoracion"])
        self.assertTrue(e["cuentas_anuales"]["url"].endswith("20260521.pdf"))      # el de 12 MB, no la rectificación de 5 MB
        self.assertTrue(e["valoracion"]["url"].endswith("20260430.pdf"))           # el rectificado del día 30
        self.assertTrue(e["participaciones"]["url"].endswith("20260706.pdf"))      # junio de 2026, no diciembre de 2025
        self.assertEqual(e["dividendo"]["fecha"], "2026-06-24")

    def test_nombre_fichero(self):
        self.assertEqual(bme.nombre_fichero("A87934741", {"tipo": "valoracion", "fecha": "2026-04-30"}), "bme/A87934741/valoracion-2026-04-30.pdf")
        self.assertEqual(bme.nombre_fichero("../../x/A1", {"tipo": "valoracion", "fecha": "../2026"}), "bme/sin-nif/valoracion-sin-fecha.pdf")

    def test_nif_valido(self):
        self.assertEqual(bme.nif_valido("A-87.934.741"), "A87934741")
        self.assertEqual(bme.nif_valido("a72793888"), "A72793888")
        self.assertIsNone(bme.nif_valido("../../x/A1"))
        self.assertIsNone(bme.nif_valido(None))

    def test_sociedad_desde_ficha_y_provincia(self):
        s = bme.sociedad_desde_ficha({"nombre": "EJEMPLO SOCIMI, S.A.", "isin": "ES0100000000", "segmento": "BME Growth", "web": "http://x", "capitalizacion": 19452103.0,
                                      "empresa": {"nif": "A-72793888", "domicilio": "PASEO DE LA HABANA 74, 28036 MADRID", "auditor": "-", "asesor_registrado": "-", "proveedor_liquidez": "-"}})
        self.assertEqual(s["nif"], "A72793888")
        self.assertIsNone(s["auditor"])
        self.assertEqual(bme.provincia_de_domicilio(s["domicilio"]), "Madrid")
        self.assertEqual(bme.provincia_de_domicilio("Gran Vía 1, 48001 Bilbao"), "Bizkaia")
        self.assertEqual(bme.provincia_de_domicilio("Calle Portal de Castilla 5, 01007 Vitoria"), "Álava")
        self.assertEqual(bme.provincia_de_domicilio("Zubieta 2, 20007 Donostia"), "Gipuzkoa")
        self.assertIsNone(bme.provincia_de_domicilio(None))


if __name__ == "__main__":
    unittest.main()


class TestCNMVGuion(unittest.TestCase):
    def test_con_guion(self):
        self.assertEqual(cnmv.con_guion("A28027399"), "A-28027399")
        self.assertEqual(cnmv.con_guion("a-28027399"), "A-28027399")
        self.assertEqual(cnmv.con_guion("raro"), "RARO")


class TestProvinciaPorCiudad(unittest.TestCase):
    def test_sin_codigo_postal(self):
        self.assertEqual(bme.provincia_de_domicilio("PRíNCIPE DE VERGARA 112, MADRID"), "Madrid")
        self.assertEqual(bme.provincia_de_domicilio("AVENIDA DIAGONAL 594, BARCELONA"), "Barcelona")
        self.assertEqual(bme.provincia_de_domicilio("Paseo de la Castellana, 52 de Madrid (España)."), "Madrid")
        self.assertEqual(bme.provincia_de_domicilio("Paseo de la Castellana 257, Madrid, España"), "Madrid")

    def test_el_codigo_postal_manda_y_la_calle_no_engana(self):
        self.assertEqual(bme.provincia_de_domicilio("CALLE BILBAO 3, 28004 MADRID"), "Madrid")
        self.assertIsNone(bme.provincia_de_domicilio("Calle Madrid 4, Getafe"))
        self.assertIsNone(bme.provincia_de_domicilio(None))


class TestPortfolio(unittest.TestCase):
    def test_emisores(self):
        from socimis.fuentes import portfolio
        em = portfolio.emisores(fixture("portfolio-mercado-recortado.html"))
        self.assertEqual([e["isin"] for e in em], ["ES0105746004", "ES0181831001", "ES0105972006"])
        ac = em[0]
        self.assertEqual((ac["ticker"], ac["nombre"], ac["pais"]), ("ACRS", "AC Residencial SOCIMI, S.A.", "ES"))
        self.assertEqual((ac["capitalizacion"], ac["cotizacion"]), (29872824.0, 1.0))
        self.assertIsNone(ac["nav_por_accion"])
        self.assertTrue(ac["socimi_en_nombre"])
        self.assertTrue(ac["url"].startswith("https://www.portfolio.exchange/portfolio-market/"))
        scr = em[1]
        self.assertEqual((scr["nav_por_accion"], scr["nav_total"], scr["capitalizacion"]), (25.09, 301080000.0, None))
        self.assertFalse(scr["socimi_en_nombre"])
        self.assertFalse(em[2]["socimi_en_nombre"])

    def test_sociedad(self):
        from socimis.fuentes import portfolio
        s = portfolio.sociedad_desde_emisor(portfolio.emisores(fixture("portfolio-mercado-recortado.html"))[0])
        self.assertEqual((s["nif"], s["isin"], s["segmento"]), (None, "ES0105746004", "Portfolio SE"))


class TestEuronext(unittest.TestCase):
    LISTADO = {"fuente": "https://live.euronext.com/en/products/equities/list", "consultado": "2026-10-27", "filas": [
        {"nombre": "AGP MALAGA SOCIMI", "isin": "ES0105478004", "simbolo": "MLAGP", "mic": "XMLI", "ultimo": "EUR 2.96", "variacion": "3.50%", "fecha": "16 May 2024", "url": "https://live.euronext.com/en/product/equities/ES0105478004-XMLI"},
        {"nombre": "EUROLOG CANOLA", "isin": "ES0105586004", "simbolo": "MLCAN", "mic": "XMLI", "ultimo": "EUR 1,320.00", "variacion": "-", "fecha": "11 Aug 2021", "url": "x"},
        {"nombre": "HAY 2 SOCIMI", "isin": "ES0106042007", "simbolo": "MLHA2", "mic": "XMLI", "ultimo": "-", "variacion": "-", "fecha": "-", "url": "x"},
        {"nombre": "EMBENTION", "isin": "ES0105639001", "simbolo": "ALUAV", "mic": "ALXP", "ultimo": "EUR 26.00", "variacion": "-", "fecha": "-", "url": "x"},
        {"nombre": "RARA", "isin": "FR0000000001", "simbolo": "X", "mic": "XMLI", "ultimo": "-", "variacion": "-", "fecha": "-", "url": "x"},
    ]}

    def test_emisores_solo_xmli_y_espanolas(self):
        from socimis.fuentes import euronext
        em = euronext.emisores(self.LISTADO)
        self.assertEqual([e["isin"] for e in em], ["ES0105478004", "ES0105586004", "ES0106042007"])
        self.assertEqual((em[0]["cotizacion"], em[0]["fecha_cotizacion"], em[0]["socimi_en_nombre"]), (2.96, "2024-05-16", True))
        self.assertEqual((em[1]["cotizacion"], em[1]["socimi_en_nombre"]), (1320.0, False))
        self.assertIsNone(em[2]["cotizacion"])
        s = euronext.sociedad_desde_emisor(em[0])
        self.assertEqual((s["nif"], s["segmento"], s["ticker"]), (None, "Euronext Access", "MLAGP"))
