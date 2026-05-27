import pandas as pd
import sqlite3

from fontTools.subset import subset

file_path = 'DGEEC_AlunosMatriculados_2017_2018.xlsx'
db_path = "AlunosMatriculados.db"

# Criar as tabelas do modelo relacional
create_tables_sql = """
CREATE TABLE IF NOT EXISTS AnoLetivo (
    CODAnoLetivo INTEGER PRIMARY KEY,
    AnoLetivo VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS Organizacao (
    CODOrganizacao INTEGER PRIMARY KEY,
    Organizacao VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS AnoEscolaridade (
    CODAnoEscolaridade INTEGER PRIMARY KEY,
    AnoEscolaridade VARCHAR(8)
);

CREATE TABLE IF NOT EXISTS NivelEnsino (
    CODNivelEnsino INTEGER PRIMARY KEY,
    NivelEnsino VARCHAR(35)
);

CREATE TABLE IF NOT EXISTS Oferta (
    CODOferta INTEGER PRIMARY KEY,
    Oferta VARCHAR(23)
);

CREATE TABLE IF NOT EXISTS Cursos (
    CODCurso INTEGER PRIMARY KEY,
    Curso VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS Orientacao (
    CODOrientacao INTEGER PRIMARY KEY,
    Orientacao VARCHAR(55)
);

CREATE TABLE IF NOT EXISTS CicloEstudos (
    CODCicloEstudos INTEGER PRIMARY KEY,
    CicloEstudos VARCHAR(9)
);

CREATE TABLE IF NOT EXISTS Sexo (
    CODSexo INTEGER PRIMARY KEY,
    Sexo VARCHAR(8)
);

CREATE TABLE IF NOT EXISTS Escola (
    CODEscola INTEGER PRIMARY KEY,
    Escola VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS Agrupamento (
    CODAgrupamento INTEGER PRIMARY KEY,
    Agrupamento VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS EscolaSede (
    CODEscolaSede INTEGER PRIMARY KEY,
    EscolaSede VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS NUTSII (
    CODNUTSII INTEGER PRIMARY KEY,
    NUTSII VARCHAR(25)
);

CREATE TABLE IF NOT EXISTS Distrito (
    CODDistrito INTEGER PRIMARY KEY,
    Distrito VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS Localizacao (
    CODEntidade INTEGER PRIMARY KEY REFERENCES Entidade(CODEntidade),
    CODConcelho INTEGER REFERENCES Concelho(CODConcelho)
);

CREATE TABLE IF NOT EXISTS NUTSIII (
    CODNUTSIII INTEGER PRIMARY KEY,
    NUTSIII VARCHAR(25),
    CODNUTSII INTEGER REFERENCES NUTSII (CODNUTSII)
);

CREATE TABLE IF NOT EXISTS Concelho (
    CODConcelho INTEGER PRIMARY KEY,
    Concelho VARCHAR(30),
    CODDistrito INTEGER REFERENCES Distrito (CODDistrito),
    CODNUTSIII INTEGER REFERENCES NUTSIII (CODNUTSIII)
);

CREATE TABLE IF NOT EXISTS Entidade (
    CODEntidade INTEGER PRIMARY KEY,
    Entidade VARCHAR(255),
    CODEscola INTEGER REFERENCES Escola (CODEscola),
    CODAgrupamento INTEGER REFERENCES Agrupamento (CODAgrupamento),
    CODEscolaSede INTEGER REFERENCES EscolaSede (CODEscolaSede),
    Rede VARCHAR(12),
    Natureza VARCHAR(20),
    Tipologia VARCHAR(3)
);

CREATE TABLE IF NOT EXISTS Inscricoes (
    CODAnoLetivo VARCHAR(10),
    CODEntidade INTEGER,
    CODOrganizacao INTEGER,
    CODAnoEscolaridade INTEGER,
    CODNivelEnsino INTEGER,
    CODOferta INTEGER,
    CODCurso INTEGER,
    CODOrientacao INTEGER,
    CODCicloEstudos INTEGER,
    CODSexo INTEGER,
    NumeroAlunosMatriculados INTEGER,
    PRIMARY KEY (
        CODEntidade, CODAnoLetivo, CODOrganizacao, CODAnoEscolaridade,
        CODNivelEnsino, CODOferta, CODCurso, CODOrientacao, CODCicloEstudos, CODSexo
    ),
    FOREIGN KEY (CODAnoLetivo) REFERENCES AnoLetivo (CODAnoLetivo),
    FOREIGN KEY (CODEntidade) REFERENCES Entidade (CODEntidade),
    FOREIGN KEY (CODOrganizacao) REFERENCES Organizacao (CODOrganizacao),
    FOREIGN KEY (CODAnoEscolaridade) REFERENCES AnoEscolaridade (CODAnoEscolaridade),
    FOREIGN KEY (CODNivelEnsino) REFERENCES NivelEnsino (CODNivelEnsino),
    FOREIGN KEY (CODOferta) REFERENCES Oferta (CODOferta),
    FOREIGN KEY (CODCurso) REFERENCES Cursos (CODCurso),
    FOREIGN KEY (CODOrientacao) REFERENCES Orientacao (CODOrientacao),
    FOREIGN KEY (CODCicloEstudos) REFERENCES CicloEstudos (CODCicloEstudos),
    FOREIGN KEY (CODSexo) REFERENCES Sexo (CODSexo)
);
"""



def fill_db():
    # Preencher as tabelas simples
    #AnoLetivo
    ano_letivo_data = excel_data.parse(sheet_name="Continente 2017-2018")["ANO LETIVO"].dropna().unique()
    ano_letivo_dict = {ano: i + 1 for i, ano in enumerate(ano_letivo_data)}
    ano_letivo_tuples = [(cod, nome) for nome, cod in ano_letivo_dict.items()]
    cursor.executemany("INSERT INTO AnoLetivo (CODAnoLetivo, AnoLetivo) VALUES (?, ?)", ano_letivo_tuples)

    # Organizacao
    organizacao_data = excel_data.parse(sheet_name="Continente 2017-2018")["ORGANIZAÇÃO"].dropna().unique()
    organizacao_dict = {org: i + 1 for i, org in enumerate(organizacao_data)}
    organizacao_tuples = [(cod, nome) for nome, cod in organizacao_dict.items()]
    cursor.executemany("INSERT INTO Organizacao (CODOrganizacao, Organizacao) VALUES (?, ?)", organizacao_tuples)

    # Ano Escolaridade
    ano_escolaridade_data = excel_data.parse(sheet_name="Continente 2017-2018")["ANO DE ESCOLARIDADE"].dropna().unique()
    ano_escolaridade_dict = {ano: i + 1 for i, ano in enumerate(ano_escolaridade_data)}
    ano_escolaridade_tuples = [(cod, nome) for nome, cod in ano_escolaridade_dict.items()]
    cursor.executemany("INSERT INTO AnoEscolaridade (CODAnoEscolaridade, AnoEscolaridade) VALUES (?, ?)", ano_escolaridade_tuples)

    # Nível de Ensino
    nivel_ensino_data = excel_data.parse(sheet_name="Continente 2017-2018")["NÍVEL DE  ENSINO"].dropna().unique()
    nivel_ensino_dict = {nivel: i + 1 for i, nivel in enumerate(nivel_ensino_data)}
    nivel_ensino_tuples = [(cod, nome) for nome, cod in nivel_ensino_dict.items()]
    cursor.executemany("INSERT INTO NivelEnsino (CODNivelEnsino, NivelEnsino) VALUES (?, ?)", nivel_ensino_tuples)

    # Oferta
    oferta_data = excel_data.parse(sheet_name="Continente 2017-2018")["OFERTA"].dropna().unique()
    oferta_dict = {oferta: i + 1 for i, oferta in enumerate(oferta_data)}
    oferta_tuples = [(cod, nome) for nome, cod in oferta_dict.items()]
    cursor.executemany("INSERT INTO Oferta (CODOferta, Oferta) VALUES (?, ?)", oferta_tuples)

    # Cursos
    curso_data = excel_data.parse(sheet_name="Continente 2017-2018")["CURSO"].dropna().unique()
    curso_dict = {curso: i + 1 for i, curso in enumerate(curso_data)}
    curso_tuples = [(cod, nome) for nome, cod in curso_dict.items()]
    cursor.executemany("INSERT INTO Cursos (CODCurso, Curso) VALUES (?, ?)", curso_tuples)

    # Orientação
    orientacao_data = excel_data.parse(sheet_name="Continente 2017-2018")["ORIENTAÇÃO"].dropna().unique()
    orientacao_dict = {orientacao: i + 1 for i, orientacao in enumerate(orientacao_data)}
    orientacao_tuples = [(cod, nome) for nome, cod in orientacao_dict.items()]
    cursor.executemany("INSERT INTO Orientacao (CODOrientacao, Orientacao) VALUES (?, ?)", orientacao_tuples)

    # Ciclo de Estudos
    ciclo_estudos_data = excel_data.parse(sheet_name="Continente 2017-2018")["CICLO DE ESTUDOS"].dropna().unique()
    ciclo_estudos_dict = {ciclo: i + 1 for i, ciclo in enumerate(ciclo_estudos_data)}
    ciclo_estudos_tuples = [(cod, nome) for nome, cod in ciclo_estudos_dict.items()]
    cursor.executemany("INSERT INTO CicloEstudos (CODCicloEstudos, CicloEstudos) VALUES (?, ?)", ciclo_estudos_tuples)

    # Sexo
    sexo_data = excel_data.parse(sheet_name="Continente 2017-2018")["SEXO"].dropna().unique()
    sexo_dict = {sexo: i + 1 for i, sexo in enumerate(sexo_data)}
    sexo_tuples = [(cod, nome) for nome, cod in sexo_dict.items()]
    cursor.executemany("INSERT INTO Sexo (CODSexo, Sexo) VALUES (?, ?)", sexo_tuples)

    # Escola
    escola_data = excel_data.parse(sheet_name="Continente 2017-2018")[["ESCOLA", "CÓDIGO DGEEC ESCOLA"]].dropna(subset=["CÓDIGO DGEEC ESCOLA"]).drop_duplicates()
    escola_tuples = [(row["CÓDIGO DGEEC ESCOLA"], row["ESCOLA"]) for i, row in escola_data.iterrows()]
    cursor.executemany("INSERT INTO Escola (CODEscola, Escola) VALUES (?, ?)", escola_tuples)

    # Agrupamento
    agrupamento_data = excel_data.parse(sheet_name="Continente 2017-2018")[["AGRUPAMENTO", "CÓDIGO DGEEC AGRUPAMENTO"]].dropna(subset=["CÓDIGO DGEEC AGRUPAMENTO"]).drop_duplicates()
    agrupamento_tuples = [(row["CÓDIGO DGEEC AGRUPAMENTO"], row["AGRUPAMENTO"]) for i, row in agrupamento_data.iterrows()]
    cursor.executemany("INSERT INTO Agrupamento (CODAgrupamento, Agrupamento) VALUES (?, ?)", agrupamento_tuples)

    # Escola Sede
    escola_sede_data = excel_data.parse(sheet_name="Continente 2017-2018")[["ESCOLA SEDE", "CÓDIGO DGEEC ESCOLA SEDE"]].dropna(subset=["CÓDIGO DGEEC ESCOLA SEDE"]).drop_duplicates()
    escola_sede_tuples = [(row["CÓDIGO DGEEC ESCOLA SEDE"], row["ESCOLA SEDE"]) for i, row in escola_sede_data.iterrows()]
    cursor.executemany("INSERT INTO EscolaSede (CODEscolaSede, EscolaSede) VALUES (?, ?)", escola_sede_tuples)

    # Distrito
    distrito_data = excel_data.parse(sheet_name="Continente 2017-2018")["DISTRITO"].dropna().unique()
    distrito_dict = {distrito: i + 1 for i, distrito in enumerate(distrito_data)}
    distrito_tuples = [(cod, nome) for nome, cod in distrito_dict.items()]
    cursor.executemany("INSERT INTO Distrito (CODDistrito, Distrito) VALUES (?, ?)", distrito_tuples)

    # NUTS II
    nutsii_data = excel_data.parse(sheet_name="Continente 2017-2018")["NUTS II (2013)"].dropna().unique()
    nutsii_dict = {nutsii: i + 1 for i, nutsii in enumerate(nutsii_data)}
    nutsii_tuples = [(cod, nome) for nome, cod in nutsii_dict.items()]
    cursor.executemany("INSERT INTO NUTSII (CODNUTSII, NUTSII) VALUES (?, ?)", nutsii_tuples)

    # NUTS III
    nutsiii_data = excel_data.parse(sheet_name="Continente 2017-2018")["NUTS III (2013)"].dropna().unique()
    nutsiii_dict = {nutsiii: i + 1 for i, nutsiii in enumerate(nutsiii_data)}
    nutsiii_data_comp = excel_data.parse(sheet_name="Continente 2017-2018")[["NUTS III (2013)", "NUTS II (2013)"]].drop_duplicates()
    nutsiii_tuples = [(nutsiii_dict.get(row["NUTS III (2013)"]), row["NUTS III (2013)"], nutsii_dict.get(row["NUTS II (2013)"]))
                    for i, row in nutsiii_data_comp.iterrows()]
    cursor.executemany("INSERT INTO NUTSIII (CODNUTSIII, NUTSIII, CODNUTSII) VALUES (?, ?, ?)", nutsiii_tuples)

    # Concelhos
    concelho_data = excel_data.parse(sheet_name="Continente 2017-2018")["CONCELHO"].dropna().unique()
    concelho_dict = {concelhos: i + 1 for i, concelhos in enumerate(concelho_data)}
    concelho_data_comp = excel_data.parse(sheet_name="Continente 2017-2018")[["CONCELHO", "DISTRITO", "NUTS III (2013)"]].drop_duplicates()
    concelho_tuples = [(concelho_dict.get(row["CONCELHO"]), row["CONCELHO"], distrito_dict.get(row["DISTRITO"]), nutsiii_dict.get(row["NUTS III (2013)"]))
                    for i, row in concelho_data_comp.iterrows()]
    cursor.executemany("INSERT INTO Concelho (CODConcelho, Concelho, CODDistrito, CODNUTSIII) VALUES (?, ?, ?, ?)", concelho_tuples)

    # Entidade
    entidade_data_comp = excel_data.parse(sheet_name="Continente 2017-2018")[["CÓDICO DGEEC ENTIDADE", "ENTIDADE", "CÓDIGO DGEEC ESCOLA", "CÓDIGO DGEEC AGRUPAMENTO", "CÓDIGO DGEEC ESCOLA SEDE", "REDE",
                                                                            "NATUREZA", "TIPOLOGIA"]].drop_duplicates()
    entidade_tuples = [(row["CÓDICO DGEEC ENTIDADE"], row["ENTIDADE"], row["CÓDIGO DGEEC ESCOLA"], row["CÓDIGO DGEEC AGRUPAMENTO"], row["CÓDIGO DGEEC ESCOLA SEDE"],
                        row["REDE"], row["NATUREZA"], row["TIPOLOGIA"]) for i, row in entidade_data_comp.iterrows()]
    cursor.executemany("INSERT INTO Entidade (CODEntidade, Entidade, CODEscola, CODAgrupamento, CODEscolaSede, Rede, Natureza, Tipologia) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", entidade_tuples)

    # Localização
    localizacao_data_comp = excel_data.parse(sheet_name="Continente 2017-2018")[["CÓDICO DGEEC ENTIDADE", "CONCELHO"]].drop_duplicates()
    localizacao_tuples = [(row["CÓDICO DGEEC ENTIDADE"], concelho_dict.get(row["CONCELHO"]))
                        for i, row in localizacao_data_comp.iterrows()]
    cursor.executemany("INSERT INTO Localizacao (CODEntidade, CODConcelho) VALUES (?, ?)", localizacao_tuples)

    # Inscrições
    inscricoes_data_comp = excel_data.parse(sheet_name="Continente 2017-2018")[["ANO LETIVO", "CÓDICO DGEEC ENTIDADE", "OFERTA", "NÍVEL DE  ENSINO", "ORGANIZAÇÃO", "CICLO DE ESTUDOS", "CURSO", "SEXO",
                                                                            "ORIENTAÇÃO", "ANO DE ESCOLARIDADE", "NÚMERO DE ALUNOS MATRICULADOS"]].drop_duplicates()
    inscricoes_tuples = [(ano_letivo_dict.get(row["ANO LETIVO"]), row["CÓDICO DGEEC ENTIDADE"], organizacao_dict.get(row["ORGANIZAÇÃO"]), ano_escolaridade_dict.get(row["ANO DE ESCOLARIDADE"]),
                        nivel_ensino_dict.get(row["NÍVEL DE  ENSINO"]), oferta_dict.get(row["OFERTA"]), curso_dict.get(row["CURSO"]), orientacao_dict.get(row["ORIENTAÇÃO"]),
                        ciclo_estudos_dict.get(row["CICLO DE ESTUDOS"]), sexo_dict.get(row["SEXO"]), row["NÚMERO DE ALUNOS MATRICULADOS"])
                        for i, row in inscricoes_data_comp.iterrows()]
    cursor.executemany("INSERT INTO Inscricoes (CODAnoLetivo, CODEntidade, CODOrganizacao, CODAnoEscolaridade, CODNivelEnsino,"
                    "CODOferta, CODCurso, CODOrientacao, CODCicloEstudos, CODSexo, NumeroAlunosMatriculados)"
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", inscricoes_tuples)

    # Fechar a conexão após terminar
    conn.commit()
    conn.close()


if __name__ == '__main__':
    excel_data = pd.ExcelFile(file_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.executescript(create_tables_sql)
    conn.commit()

    fill_db