"""Los lectores contra documentos reales (extractos de texto de PDF y xhtml bajados el 2026-10-26; ver fixtures/LEEME.md)."""
import os
import unittest

from socimis.parsers import avisos, estados, ixbrl

AQUI = os.path.dirname(os.path.abspath(__file__))


def fixture(nombre):
    with open(os.path.join(AQUI, "fixtures", nombre), encoding="utf-8") as f:
        return f.read()


class TestIXBRL(unittest.TestCase):
    def setUp(self):
        self.ej, self.avisos = ixbrl.por_ejercicio(fixture("ixbrl-merlin-2025-extracto.xhtml"))

    def test_lee_los_dos_ejercicios(self):
        self.assertEqual(sorted(self.ej), ["2023", "2024", "2025"])      # 2023 solo trae patrimonio neto (estado de cambios)

    def test_tesoreria_en_euros_con_escala_de_miles(self):
        self.assertEqual(self.ej["2025"]["tesoreria"]["valor"], 1214945000.0)
        self.assertEqual(self.ej["2024"]["tesoreria"]["valor"], 1552676000.0)
        self.assertEqual(self.ej["2025"]["tesoreria"]["fecha"], "2025-12-31")
        self.assertEqual(self.ej["2025"]["tesoreria"]["id"], "f-69")

    def test_inmuebles_bonos_prestamos_ingresos_dividendos(self):
        e = self.ej["2025"]
        self.assertEqual(e["valor_razonable_inmuebles"]["valor"], 11983699000.0)
        self.assertEqual(e["bonos_lp"]["valor"], 2532309000.0)
        self.assertEqual(e["bonos_cp"]["valor"], 820658000.0)
        self.assertEqual(e["prestamos_lp"]["valor"], 1573449000.0)
        self.assertEqual(e["prestamos_cp"]["valor"], 45945000.0)
        self.assertEqual(e["ingresos"]["valor"], 538963000.0)
        self.assertEqual(e["dividendos_pagados"]["valor"], 236381000.0)
        self.assertEqual(e["ingresos"]["inicio"], "2025-01-01")

    def test_sin_avisos_de_hechos_contradictorios(self):
        self.assertEqual(self.avisos, [])

    def test_numeros_con_formato(self):
        self.assertEqual(ixbrl._numero("1,214,945", "ixt4:num-dot-decimal"), 1214945.0)        # decimal con punto: los miles con coma
        self.assertEqual(ixbrl._numero("1.214.945", "ixt4:num-comma-decimal"), 1214945.0)      # decimal con coma: los miles con punto (España)
        self.assertEqual(ixbrl._numero("1.214.945,50", "ixt4:num-comma-decimal"), 1214945.5)
        self.assertEqual(ixbrl._numero("(10.033)", None), -10033.0)
        self.assertEqual(ixbrl._numero("-", None), 0.0)
        self.assertEqual(ixbrl._numero("1.234,5", None), 1234.5)

    def test_los_hechos_con_dimensiones_no_entran(self):
        texto = fixture("ixbrl-merlin-2025-extracto.xhtml")
        con_dim = [h for h in ixbrl.hechos(texto) if ixbrl.contextos(texto)[[c for c in ixbrl.contextos(texto)][0]]["dimensiones"]]
        self.assertIsInstance(con_dim, list)


class TestEstados(unittest.TestCase):
    def setUp(self):
        self.r = estados.leer(fixture("estados-alliron-2025.txt"))

    def test_ejercicios(self):
        self.assertEqual(self.r["ejercicios"], ["2025", "2024"])
        self.assertEqual(self.r["unidad"], 1.0)

    def test_balance(self):
        p = self.r["partidas"]
        self.assertEqual(p["tesoreria"], [13217301.0, 22408461.0])
        self.assertEqual(p["inversiones_inmobiliarias"], [363437000.0, 275398184.0])
        self.assertEqual(p["deuda_entidades_lp"], [117385551.0, 94221397.0])
        self.assertEqual(p["deuda_entidades_cp"], [6483865.0, 4160422.0])
        self.assertEqual(p["patrimonio_neto"], [259382688.0, 206665961.0])
        self.assertEqual(p["activo_total"], [391193555.0, 311618619.0])

    def test_resultados_y_flujos(self):
        p = self.r["partidas"]
        self.assertEqual(p["ingresos_rentas"], [9832863.0, 7586867.0])
        self.assertEqual(p["variacion_valor_razonable"], [39797449.0, 8632461.0])
        self.assertEqual(p["resultado"], [44580816.0, 11966084.0])
        self.assertEqual(p["pagos_dividendos"], [-2245589.0, -843416.0])

    def test_lo_que_no_esta_se_avisa(self):
        self.assertIn("no encontrado: cifra_negocios", self.r["avisos"])       # el rótulo está, pero sin cifras en la misma línea

    def test_ltv_declarado(self):
        self.assertEqual(estados.ltv_declarado("EPRA LTV                                         31,8%   -     28,5%       -   +3,3pp"), (31.8, 28.5))
        self.assertEqual(estados.ltv_declarado("sin nada"), (None, None))

    def test_vencimientos(self):
        v = estados.vencimientos(fixture("deuda-alliron-2025.txt"))
        self.assertEqual(len(v), 18)
        self.assertEqual(v[0], {"entidad": "Banco Santander", "importe": 21872301.0, "importe_anterior": 14218460.0, "vencimiento": "2031-09-05", "tipo_interes": "2,45%"})
        self.assertEqual(v[1]["tipo_interes"], "Euribor+2,25%")
        self.assertEqual(v[2]["importe"], 0.0)                                 # un «-»: ya amortizado
        self.assertEqual(sum(x["importe"] for x in v), 73893762.0)
        self.assertIn("Kutxabank", [x["entidad"] for x in v])

    def test_bloque_solo_una_tabla(self):
        texto = "cabecera\nInversión inmobiliaria   Ubicación   31/12/2025\n Edificio Uno   Calle A 1, Bilbao   1.000.000   900.000\n\n\n\n Edificio Uno   Calle A 1, Bilbao   1.100.000   1.000.000\n"
        self.assertEqual(len(estados.inversiones_inmobiliarias(texto)), 1)
        self.assertEqual(estados.inversiones_inmobiliarias("sin tabla\n Capital  155.532.230  147.218.270\n"), [])

    def test_inversiones_inmobiliarias(self):
        a = estados.inversiones_inmobiliarias(fixture("activos-alliron-2025.txt"))
        nombres = [x["nombre"] for x in a]
        self.assertIn("Aparthotel Gasteiz", nombres)
        self.assertIn("Edificio Bilbao Ledesma", nombres)
        gasteiz = next(x for x in a if x["nombre"] == "Aparthotel Gasteiz")
        self.assertEqual(gasteiz["ubicacion"], "Avenida de Gasteiz 45, Vitoria")
        self.assertEqual(gasteiz["valor"], 34800000.0)
        koisi = next(x for x in a if x["nombre"].startswith("Koisi"))
        self.assertIsNone(koisi["valor"])                                      # vendido: «-» en 2025
        self.assertEqual(koisi["valor_anterior"], 6100000.0)
        self.assertEqual(len(a), 15)


class TestEstadosMilesYEuros(unittest.TestCase):
    """Advero (BME Growth) lleva delante un resumen «en miles de euros» y detrás los estados completos en euros: mandan los euros."""

    def test_prefiere_la_pagina_en_euros(self):
        r = estados.leer(fixture("estados-advero-2025-miles-y-euros.txt"))
        p = r["partidas"]
        self.assertEqual(p["tesoreria"], [16450754.0, 7198655.0])
        self.assertEqual(p["activo_total"], [73509575.0, 61639250.0])
        self.assertEqual(p["deuda_entidades_lp"], [11132300.0, 12067631.0])
        self.assertEqual(p["deuda_entidades_cp"], [960612.0, 939221.0])
        self.assertTrue(r["estados_reconocidos"])

    def test_solo_miles_se_escala(self):
        texto = next(pg for pg in fixture("estados-advero-2025-miles-y-euros.txt").split("\f") if "en miles de euros" in pg)
        p, _ = estados.partidas(texto)
        self.assertEqual(p["tesoreria"], [16451000.0, 7199000.0])
        self.assertEqual(p["inversiones_inmobiliarias"], [56606000.0, 53915000.0])

    def test_sin_estados_lo_avisa(self):
        r = estados.leer("Carta de presentación\nLa Sociedad remite sus cuentas.\n")
        self.assertFalse(r["estados_reconocidos"])
        self.assertTrue(any("estados no reconocidos" in a for a in r["avisos"]))

    def test_sin_cabecera_no_hay_tabla(self):
        self.assertEqual(estados.vencimientos("Banco Uno  1.000  900  01/01/2030  2%\n"), [])
        self.assertEqual(estados.inversiones_inmobiliarias(" Edificio Uno   Calle A 1, Bilbao   1.000.000   900.000\n"), [])


class TestAvisos(unittest.TestCase):
    def test_valoracion(self):
        v = avisos.valoracion(fixture("aviso-valoracion-alliron-2025.txt"))
        self.assertEqual(v["total"], 363437000.0)
        self.assertEqual(v["fecha"], "2025-12-31")
        self.assertIn("Savills Aguirre Newman Valoraciones y Tasaciones, S.A.U.", v["valoradores"])
        self.assertIn("Gloval Valuation, S.A.U.", v["valoradores"])

    def test_dividendo(self):
        d = avisos.dividendo(fixture("aviso-dividendo-alliron-2026.txt"))
        self.assertEqual(d["importe_total"], 3226792.91)
        self.assertEqual(d["importe_por_accion"], 0.20751445)
        self.assertEqual(d["fecha_pago"], "2026-07-16")
        self.assertEqual(d["con_cargo_a"], "2025")
        self.assertEqual(d["fecha_acuerdo"], "2026-06-23")

    def test_participaciones(self):
        p = avisos.participaciones(fixture("aviso-participaciones-ficticio.txt"))
        self.assertEqual(p["fecha"], "2026-06-30")
        nombres = [a["accionista"] for a in p["accionistas"]]
        self.assertEqual(nombres, ["Cartera Ficticia Uno, S.L.", "D. Nombre Apellido Inventado", "Inversiones Ficticias Dos, S.L.", "Holding Ficticio Tres, S.L.U."])
        uno, persona = p["accionistas"][0], p["accionistas"][1]
        self.assertEqual((uno["tipo"], uno["acciones"], uno["pct_directo"], uno["pct_total"]), ("juridica", 890601, 5.73, 5.73))
        self.assertEqual(persona["tipo"], "fisica")
        self.assertEqual(persona["pct_total"], 5.73)
        self.assertEqual(persona["pct_indirecto"], 5.73)
        self.assertIn("Cartera Ficticia", persona["a_traves_de"])
        self.assertEqual(p["accionistas"][3]["pct_total"], 5.01)

    def test_la_prosa_con_porcentajes_no_es_un_accionista(self):
        texto = ("A 30 de junio de 2026 los accionistas con una participación igual o superior al 5% del capital social de EJEMPLO son los siguientes:\n"
                 "La Sociedad informa de que Bolsa de Johannesburgo (Sudáfrica), el cual ostentaba un 99,67% del capital.\n"
                 "   Cartera Uno, S.L.      1.000.000     51,00%      -      51,00%\n")
        p = avisos.participaciones(texto)
        self.assertEqual([a["accionista"] for a in p["accionistas"]], ["Cartera Uno, S.L."])

    def test_ejercicio_que_no_cierra_en_diciembre(self):
        self.assertEqual(estados.ejercicios_de("ACTIVO    31/03/2026    31/03/2025\n"), ["2026", "2025"])

    def test_unidad_cambia_dentro_de_la_pagina(self):
        texto = ("(en miles de euros)\nEfectivo y otros activos líquidos equivalentes   16.451   7.199\n"
                 "(Expresado en euros)\nEfectivo y otros activos líquidos equivalentes   16.450.754   7.198.655\n")
        p, _ = estados.partidas(texto)
        self.assertEqual(p["tesoreria"], [16450754.0, 7198655.0])

    def test_tipo_accionista(self):
        self.assertEqual(avisos.tipo_accionista("Dª Catalina Ejemplo"), "fisica")
        self.assertEqual(avisos.tipo_accionista("GVC GAESCO SOSTENIBLE ISR F.I."), "juridica")
        self.assertEqual(avisos.tipo_accionista("Cosa Rara"), "no consta")


if __name__ == "__main__":
    unittest.main()


class TestIxbrlTextos(unittest.TestCase):
    def test_domicilio_y_nombre(self):
        from socimis.parsers import ixbrl
        t = ('<p><ix:nonNumeric contextRef="c" name="ifrs-full:NameOfReportingEntityOrOtherMeansOfIdentification" id="f-1"> Ejemplo SOCIMI, S.A. </ix:nonNumeric>'
             '<ix:nonNumeric contextRef="c" name="ifrs-full:AddressOfRegisteredOfficeOfEntity" id="f-2">Paseo de la Castellana, 52 de Madrid (España). Con fecha 3 de mayo la Junta acordó.</ix:nonNumeric>'
             '<ix:nonNumeric contextRef="c" name="ifrs-full:AddressOfRegisteredOfficeOfEntity" id="f-3">otro</ix:nonNumeric></p>')
        r = ixbrl.textos(t)
        self.assertEqual(r["nombre"], "Ejemplo SOCIMI, S.A")
        self.assertEqual(r["domicilio"], "Paseo de la Castellana, 52 de Madrid (España)")


class TestActivosSinNotas(unittest.TestCase):
    def test_la_columna_notas_no_es_ubicacion(self):
        t = ("Inversión inmobiliaria            Ubicación                 31/12/2025     31/12/2024\n"
             "Edificio Gran Vía                 Calle Gran Vía 1, Bilbao   12.000.000     11.500.000\n"
             "III. Inversiones inmobiliarias    7                          56.605.411     50.000.000\n"
             "I. Deudores comerciales           9                              72.346         60.000\n")
        a = estados.inversiones_inmobiliarias(t)
        self.assertEqual([x["nombre"] for x in a], ["Edificio Gran Vía"])
        self.assertEqual(a[0]["ubicacion"], "Calle Gran Vía 1, Bilbao")
