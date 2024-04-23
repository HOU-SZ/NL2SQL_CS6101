import datetime
import traceback

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv
from pgvector.asyncpg import register_vector
import asyncpg
import asyncio
import os
import httpx
import sys

load_dotenv()

NL2SQL_DB_HOST = os.getenv("NL2SQL_DB_HOST")
NL2SQL_DB_PORT = os.getenv("NL2SQL_DB_PORT")
NL2SQL_DB_USER = os.getenv("NL2SQL_DB_USER")
NL2SQL_DB_PASSWORD = os.getenv("NL2SQL_DB_PASSWORD")
NL2SQL_DB_NAME = os.getenv("NL2SQL_DB_NAME")
NL2SQL_EMBEDDING_SERVICE_URL = os.getenv(
    "NL2SQL_EMBEDDING_SERVICE_URL", default="http://localhost:18000"
)
NL2SQL_EMBEDDING_MODEL = os.getenv("NL2SQL_EMBEDDING_MODEL", default="m3e-base")

NL2SQL_TASK_SERVICE_PORT = int(os.getenv("NL2SQL_TASK_SERVICE_PORT", default=15000))

MAX_RETRIES = 3
TIMEOUT = 10  # in seconds

pool = None


class Example(BaseModel):
    id: int | None
    scene_id: int | None
    user_query: str | None
    sql_query: str | None
    create_time: datetime.datetime | None
    update_time: datetime.datetime | None
    embedding: list[float] | None


async def get_db():
    """Dependency to get the DB connection"""
    if pool is None:
        raise HTTPException(status_code=500, detail="Database pool not available")
    conn = await pool.acquire()
    try:
        yield conn
    finally:
        await pool.release(conn)


app = FastAPI()


@app.on_event("startup")
async def startup_event():
    global pool
    dsn = f"postgresql://{NL2SQL_DB_USER}:{NL2SQL_DB_PASSWORD}@{NL2SQL_DB_HOST}:{NL2SQL_DB_PORT}/postgres"

    try:
        pool = await asyncpg.create_pool(dsn=dsn)
    except asyncpg.CannotConnectNowError:
        print(
            "Error: Cannot connect to the PostgreSQL server. Check your database configurations."
        )
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

    print("Default pool created.")
    await init_db()


async def create_pool():
    global pool
    dsn = f"postgresql://{NL2SQL_DB_USER}:{NL2SQL_DB_PASSWORD}@{NL2SQL_DB_HOST}:{NL2SQL_DB_PORT}/{NL2SQL_DB_NAME}"
    try:
        tmp_conn = await asyncpg.connect(dsn=dsn)
        await tmp_conn.execute("CREATE EXTENSION IF NOT EXISTS VECTOR SCHEMA public;")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        await tmp_conn.close()

    async def init_pgvector(conn):
        await register_vector(conn)

    try:
        pool = await asyncpg.create_pool(dsn=dsn, init=init_pgvector)
    except asyncpg.CannotConnectNowError:
        print(
            f"Error: Cannot connect to the database {NL2SQL_DB_NAME}. Check your database configurations."
        )
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
    print("App db pool created.")


async def init_db():
    async with pool.acquire() as conn:
        # Check if the database exists
        db_exists = await conn.fetchval(
            """
            SELECT EXISTS (SELECT datname FROM pg_database WHERE datname = $1);
        """,
            NL2SQL_DB_NAME,
        )

        # If not, create it
        if not db_exists:
            print("Creating database ...")
            await conn.execute(f'CREATE DATABASE "{NL2SQL_DB_NAME}";')

    # Close default pool and create a new pool for our database
    await pool.close()
    await create_pool()

    async with pool.acquire() as conn:
        # Check if the table exists
        exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE  table_schema = 'public'
                AND    table_name   = 'examples'
            );
        """
        )

        # If not, create it
        if not exists:
            print("Creating table ...")
            await conn.execute(
                """
                CREATE TABLE examples (
                    id SERIAL PRIMARY KEY,
                    scene_id INT NOT NULL,
                    user_query TEXT NOT NULL,
                    sql_query TEXT NOT NULL,
                    embedding vector(4096) NOT NULL,
                    create_time TIMESTAMP NOT NULL DEFAULT NOW(),
                    update_time TIMESTAMP NOT NULL DEFAULT NOW()
                );
                CREATE UNIQUE INDEX idx_unique_scene_id_user_query ON examples(scene_id, user_query);
            """
            )


async def get_embedding_from_service(text: str, pad_to_size=4096) -> list:
    for retry in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                payload = {"model": NL2SQL_EMBEDDING_MODEL, "sentence": text}
                response = await client.post(
                    NL2SQL_EMBEDDING_SERVICE_URL + "/api/v1/embeddings", json=payload
                )

            if response.status_code == 200:
                response_json = response.json()["data"]
                embedding = response_json.get("embedding", [])
                if len(embedding) < pad_to_size:
                    embedding += [0.0] * (pad_to_size - len(embedding))
                return embedding
            else:
                # Handle error or raise an exception based on your requirements
                raise HTTPException(
                    status_code=500, detail=f"Error getting embedding: {response.text}"
                )

        except (httpx.RequestError, HTTPException) as e:
            if retry == MAX_RETRIES - 1:  # 如果是最后一次重试还是失败，抛出异常
                raise e
            # 如果不是最后一次重试，稍等片刻再进行下一次重试
            await asyncio.sleep(1)  # 延迟1秒再重试


@app.post("/api/v1/examples", response_model=Example, status_code=201)
async def insert_example(example: Example, conn=Depends(get_db)):
    scene_id = example.scene_id
    user_query = example.user_query
    sql_query = example.sql_query

    embedding = await get_embedding_from_service(user_query)

    sql_insert = """
    INSERT INTO examples(scene_id, user_query, sql_query, embedding)
        VALUES($1, $2, $3, $4)
        RETURNING id, scene_id, user_query, sql_query, create_time, update_time;
    """

    for retry in range(MAX_RETRIES):
        try:
            record = await asyncio.wait_for(
                conn.fetchrow(sql_insert, scene_id, user_query, sql_query, embedding),
                timeout=TIMEOUT,
            )
            return Example(**dict(record.items()))
        except (asyncio.TimeoutError, Exception) as e:
            if retry < MAX_RETRIES - 1:  # Check if we should retry
                print(f"Attempt {retry + 1} failed. Retrying...")
                await asyncio.sleep(1 << retry)
    else:  # If it's the last retry, log the error and raise an exception
        print(
            f"Error inserting example after {MAX_RETRIES} attempts: {e}",
            traceback.format_exc(),
        )
        raise HTTPException(
            status_code=500, detail=f"Max retries reached.Error inserting example: {e}"
        )


@app.post("/api/v1/examplesByInfo")
async def list_examples(request: Request, conn=Depends(get_db)):
    data = await request.json()
    scene_id = data["scene_id"]

    query = """
            SELECT id, scene_id,  user_query, sql_query, create_time, update_time
            FROM examples WHERE scene_id = $1;
        """
    try:
        records = await conn.fetch(query, scene_id)
        if not records:
            records = []
        examples = [Example(**dict(record.items())).dict() for record in records]
        return examples
    except Exception as e:
        print(f"Error listing examples: {e}")  # for debugging purpose
        raise HTTPException(status_code=500, detail=f"Error listing examples: {e}")


@app.delete("/api/v1/examples/{id}")
async def delete_example_by_id(id: int, conn=Depends(get_db)):
    query = """
        DELETE FROM examples WHERE id = $1;
    """
    try:
        await conn.execute(query, id)
        return JSONResponse(
            content={"message": "Example deleted successfully"}, status_code=200
        )
    except Exception as e:
        print(f"Error deleting example: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting example: {e}")


@app.post("/api/v1/findExamples")
async def find_examples(request: Request, conn=Depends(get_db)):
    data = await request.json()
    query_to_search = data["natural_language_query"]
    scene_id = data["scene_id"]
    limit_num = data["limit_num"]

    embedding_to_search = await get_embedding_from_service(query_to_search)

    async with pool.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT scene_id,  user_query, sql_query, create_time, update_time, 1 - (embedding <=> $1) AS cos_similarity
            FROM examples WHERE scene_id=$2 and user_query != $3 ORDER BY cos_similarity DESC LIMIT $4
        """,
            embedding_to_search,
            scene_id,
            query_to_search,
            limit_num,
        )

    results = [[rec["user_query"], rec["sql_query"]] for rec in records]
    return JSONResponse(content=results, status_code=200)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=NL2SQL_TASK_SERVICE_PORT)
