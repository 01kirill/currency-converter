# Описание API

Все эндпоинты доступны по базовому URL:

`http://localhost:8000/api/v1`

Интерактивная документация: `http://localhost:8000/docs` (Swagger, можно отправлять запросы) и `http://localhost:8000/redoc`.

## Общие правила

- **Деньги и курсы** передаются строками: `"100.00"`, `"0.8916116033"`. В запросе сумму можно передать и числом.
- **Коды валют** — ISO 4217, три заглавные латинские буквы: `USD`, `EUR`, `BYN`. Поддерживаются BYN и все валюты с ежедневным курсом НБ РБ.
- **Даты** — `YYYY-MM-DD`. Время в ответах — ISO 8601 с часовым поясом.
- **Ошибки** возвращаются в формате:

  ```json
  {"detail": "Deal with id aef7b866-ca72-4157-9d56-028dc06f316d not found"}
  ```

  Исключение — ошибки формата запроса (не тот тип, нет поля). Их возвращает FastAPI со списком в `detail`:

  ```json
  {
    "detail": [
      {
        "type": "decimal_parsing",
        "loc": ["body", "amount"],
        "msg": "Input should be a valid decimal",
        "input": "abc"
      }
    ]
  }
  ```

| Код | Когда |
| --- | --- |
| `404` | сделка не найдена |
| `409` | по сделке уже принято решение |
| `422` | неверные данные: формат запроса, код валюты, сумма, одинаковые валюты, неподдерживаемая валюта, перевёрнутый период |
| `503` | курсы НБ РБ на сегодня ещё не загружены, повторите позже |

## Сделки

### Объект сделки

Все эндпоинты сделок возвращают сделку в одном формате:

| Поле | Тип | Описание |
| --- | --- | --- |
| `id` | UUID | идентификатор сделки |
| `amount` | строка | сумма, которую отдаёт клиент, в `from_currency` |
| `from_currency` | строка | валюта, которую отдаёт клиент |
| `to_currency` | строка | валюта, которую получает клиент |
| `rate` | строка | сколько `to_currency` за 1 единицу `from_currency`; фиксируется при создании |
| `converted_amount` | строка | сумма к выдаче в `to_currency`, 2 знака после запятой |
| `status` | строка | `pending`, `accepted` или `declined` |
| `created_at` | datetime | время создания |
| `resolved_at` | datetime или `null` | время подтверждения или отклонения; `null`, пока сделка не завершена |

---

#### `POST /deals`

Этап 1 обмена: рассчитать обмен по курсам НБ РБ на сегодня и создать сделку в статусе `pending`.

| Поле тела | Обязательное | Описание |
| --- | --- | --- |
| `amount` | да | сумма в исходной валюте, больше 0, не больше 2 знаков после запятой |
| `from_currency` | да | исходная валюта |
| `to_currency` | да | целевая валюта, отличная от исходной |

**Пример запроса (cURL):**

```bash
curl -X POST "http://localhost:8000/api/v1/deals" \
  -H "Content-Type: application/json" \
  -d '{"amount": "100.00", "from_currency": "USD", "to_currency": "EUR"}'
```

**Успешный ответ `201 Created`:**

```json
{
  "id": "aef7b866-ca72-4157-9d56-028dc06f316d",
  "amount": "100.00",
  "from_currency": "USD",
  "to_currency": "EUR",
  "rate": "0.8916116033",
  "converted_amount": "89.16",
  "status": "pending",
  "created_at": "2026-10-19T12:00:00+03:00",
  "resolved_at": null
}
```

**Ошибки:**

| Код | Пример `detail` |
| --- | --- |
| `422` | `"Invalid currency code: 'usd'"` |
| `422` | `"Currency 'THB' is not supported"` |
| `422` | `"Initial currency must differ from target currency"` |
| `422` | `"Amount value must be positive"` |
| `422` | `"Amount value must have at most 2 decimal places"` |
| `503` | `"Exchange rates for 2026-10-19 are not loaded yet"` |

---

#### `POST /deals/{deal_id}/resolve`

Этап 2 обмена: подтвердить или отклонить сделку. `deal_id` — `id` из ответа `POST /deals`.

| Поле тела | Обязательное | Описание |
| --- | --- | --- |
| `accept` | да | `true` — подтвердить, `false` — отклонить |

**Пример запроса (cURL):**

```bash
curl -X POST "http://localhost:8000/api/v1/deals/aef7b866-ca72-4157-9d56-028dc06f316d/resolve" \
  -H "Content-Type: application/json" \
  -d '{"accept": true}'
```

**Успешный ответ `200 OK`:**

```json
{
  "id": "aef7b866-ca72-4157-9d56-028dc06f316d",
  "amount": "100.00",
  "from_currency": "USD",
  "to_currency": "EUR",
  "rate": "0.8916116033",
  "converted_amount": "89.16",
  "status": "accepted",
  "created_at": "2026-10-19T09:00:00Z",
  "resolved_at": "2026-10-19T12:00:00+03:00"
}
```

**Ошибки:**

| Код | Пример `detail` |
| --- | --- |
| `404` | `"Deal with id aef7b866-ca72-4157-9d56-028dc06f316d not found"` |
| `409` | `"Conclusion for deal with id aef7b866-ca72-4157-9d56-028dc06f316d already made"` |
| `422` | `deal_id` не UUID, нет поля `accept` |

---

#### `GET /deals/pending`

Список незавершённых сделок (статус `pending`), сначала самые старые. Отклонённые и подтверждённые сделки в список не попадают.

**Пример запроса (cURL):**

```bash
curl -X GET "http://localhost:8000/api/v1/deals/pending"
```

**Успешный ответ `200 OK`:**

```json
[
  {
    "id": "aef7b866-ca72-4157-9d56-028dc06f316d",
    "amount": "100.00",
    "from_currency": "USD",
    "to_currency": "EUR",
    "rate": "0.8916116033",
    "converted_amount": "89.16",
    "status": "pending",
    "created_at": "2026-10-19T09:00:00Z",
    "resolved_at": null
  }
]
```

Если незавершённых сделок нет — `[]`.

## Отчёты

#### `GET /reports/deals`

Агрегированные данные по **подтверждённым** сделкам за период. Сделка попадает в период по дате подтверждения (`resolved_at`) в часовом поясе Минска.

| Query-параметр | Обязательный | Описание |
| --- | --- | --- |
| `date_from` | да | первый день периода, `YYYY-MM-DD` |
| `date_to` | да | последний день периода включительно, не раньше `date_from` |
| `currency` | нет | только эта валюта; без параметра — все валюты |

| Поле строки | Описание |
| --- | --- |
| `currency` | валюта |
| `received_amount` | пришло в кассу: сумма `amount` сделок, где это исходная валюта |
| `paid_out_amount` | ушло из кассы: сумма `converted_amount` сделок, где это целевая валюта |
| `deals_count` | количество сделок с этой валютой |

Одна сделка учитывается в двух строках — по исходной и по целевой валюте.

**Пример запроса (cURL):**

```bash
curl -X GET "http://localhost:8000/api/v1/reports/deals?date_from=2026-10-19&date_to=2026-10-19"
```

**Успешный ответ `200 OK`:**

```json
[
  {
    "currency": "EUR",
    "received_amount": "0.00",
    "paid_out_amount": "89.16",
    "deals_count": 1
  },
  {
    "currency": "USD",
    "received_amount": "100.00",
    "paid_out_amount": "0.00",
    "deals_count": 1
  }
]
```

С параметром `currency=USD` вернётся только строка USD. Если сделок за период нет — `[]`.

**Ошибки:**

| Код | Пример `detail` |
| --- | --- |
| `422` | `"date_from must not be later than date_to"` |
| `422` | `"Invalid currency code: 'usd'"` |
| `422` | нет `date_from` или `date_to`, дата не в формате `YYYY-MM-DD` |
