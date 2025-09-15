from sqlalchemy import create_engine, text, Table, Column, Integer, String, Float, MetaData, BigInteger
from sqlalchemy.orm import sessionmaker
import pandas as pd
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Función para mapear tipos de datos de Pandas a SQLAlchemy
def mapear_tipos(columna):
    if pd.api.types.is_integer_dtype(columna):
        return BigInteger
    elif pd.api.types.is_float_dtype(columna):
        return Float
    elif pd.api.types.is_string_dtype(columna):
        return String
    else:
        return String  # Por defecto, cualquier otro tipo se mapea como String

# Función para cargar datos de un archivo Excel a PostgreSQL
def cargar_excel_a_postgresql(file_path, sheet_name, db_url, table_name):
    try:
        # Leer el archivo Excel
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        logger.info(f"Hoja '{sheet_name}' del archivo Excel leída correctamente.")
        
        # Conectar a PostgreSQL
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Definir la tabla con SQLAlchemy
        metadata = MetaData()

        # Crear una estructura de tabla con un campo 'id' como llave primaria
        tabla = Table(
            table_name, metadata,
            Column('id', Integer, primary_key=True),  # Definición del campo id como llave primaria
            *(Column(col_name, mapear_tipos(df[col_name])) for col_name in df.columns if col_name != 'id')  # Otras columnas
        )
        
        try:
            # Borrar todo el contenido de la tabla y reiniciar el índice
            session.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"))
            session.commit()
            logger.info(f"Todo el contenido de la tabla '{table_name}' ha sido eliminado y el índice reiniciado.")

            # Cargar los datos en la tabla
            df.to_sql(table_name, engine, if_exists='append', index=False)
            logger.info("Datos cargados exitosamente en PostgreSQL.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error durante la carga de datos: {e}")
            raise
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error: {e}")

def cargar_excel_a_postgresql_delete(file_path, sheet_name, db_url, table_name):
    try:
        # Leer el archivo Excel
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        logger.info(f"Hoja '{sheet_name}' del archivo Excel leída correctamente.")
        
        # Conectar a PostgreSQL
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Definir la tabla con SQLAlchemy
        metadata = MetaData()

        # Crear una estructura de tabla con un campo 'id' como llave primaria
        tabla = Table(
            table_name, metadata,
            Column('id', Integer, primary_key=True),  # Definición del campo id como llave primaria
            *(Column(col_name, mapear_tipos(df[col_name])) for col_name in df.columns if col_name != 'id')  # Otras columnas
        )
        
        try:
             # Eliminar la tabla si existe
            session.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            session.commit()
            logger.info(f"Tabla '{table_name}' eliminada si existía.")

            # Crear la tabla en la base de datos
            metadata.create_all(engine)
            logger.info(f"Tabla '{table_name}' creada con éxito.")

            # Cargar los datos en la tabla
            df.to_sql(table_name, engine, if_exists='append', index=False)
            logger.info("Datos cargados exitosamente en PostgreSQL.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error durante la carga de datos: {e}")
            raise
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error: {e}")

# Parámetros
ruta_carpeta = os.path.join('..', 'bd')
file_path = os.path.join(ruta_carpeta, 'conceptos_fijos_y_variables.xlsx')
sheet_name = 'Page 001'
db_url = os.getenv('DATABASE_URL')
table_name = 'conceptos_fijos_y_variables'

# Llamada a la función
cargar_excel_a_postgresql_delete(file_path, sheet_name, db_url, table_name)
