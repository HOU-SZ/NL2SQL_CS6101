# NL2SQL_CS6101
Implement [MAC-SQL](https://github.com/wbbeyourself/MAC-SQL) as a backend service.

## Some changes:
 - Change database schema representation to code representation
 - Change foreign keys representation to dictionary representation
 - Use [DIN-SQL](https://github.com/MohammadrezaPourreza/Few-shot-NL2SQL-with-prompting) self-correction in the refiner

## Setup
Set up environment
```
conda create -n nl2sql_cs6101 python=3.10
conda activate nl2sql_cs6101
pip install -r requirements.txt
```
Set LLM
 - If use OpenAI LLMs, change the API_KEY in [app/core/llm.py](app/core/llm.py) to your own key
 - If use self-deployed LLMs, add/change corrsponding code in [app/core/llm.py](app/core/llm.py)

Set Database
 - Change the ds_url in [app/app.py](app/app.py) to your database url
 - Change the corresponding content in the [app/datasource.json](app/datasource.json)


## Run
```
cd app
python app.py
```
The service will start at port 18080

## Request format
 - Request url: localhost:18080/predict
 - Request body Content-Type: application/json
```
{
    "natural_language_query": "Show name, country, age for all singers ordered by age from the oldest to the youngest."
}
```

## Response format
```
{
    "success": False,
    "message": "Content-Type must be application/json"
}
```
or 
```
{
    "success": true,
    "sql_queries": [
        "SELECT \"Name\", \"Country\", \"Age\"     FROM singer     ORDER BY \"Age\" DESC"
    ]
}
```