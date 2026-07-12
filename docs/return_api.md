# Returns API


## GET return candidate:
Wymaga autoryzacji użytkownika oraz podania klucza X-API-KEY.
W odpowiedzi otrzymamy dane podstawowe kandydata na zwrot oraz listę itemów, które są możliwe do zwrotu. 

`GET /api/returns/V1/test-channel-pl/orders/{order_id}/returns`:
```json
{
    "meta": {
        "status": "OK",
        "message": "",
        "messages": [],
        "regional": {
            "language": null,
            "currency": null,
            "country": null
        }
    },
    "data": {
        "order_id": "efcd08b4-d229-4c17-94f4-04083e0a338f",
        "address": {
            "email": "customer@example.com",
            "firstname": "Test",
            "lastname": "Testowicz",
            "country_code": "PL",
            "city": "Warsaw",
            "postcode": "00-000",
            "street": "test street 89",
            "dialling_code": "+48",
            "telephone": "500500500",
            "company": ""
        },
        "items_returnable": {
            "MAX-36-Czarny": {
                "quantity": "6",
                "name": "MAX-36-Czarny"
            }
        }
    }
}

```
## GET solution/methods of return candidate:
Wymaga autoryzacji użytkownika oraz podania klucza X-API-KEY.
W odpowiedzi otrzymamy dane metody i rozwiązania kandydata na zwrot. Po jednym z nich musi zostać wybrany przez użytkownika, aby utworzyć zwrot.

`GET /api/returns/V1/<channel_idx>/orders/{order_id}/returns_extra`:
```json
{
    "meta": {
        "status": "OK",
        "message": "",
        "messages": [],
        "regional": {
            "language": null,
            "currency": null,
            "country": null
        }
    },
    "data": {
        "return_solutions": [
            {
                "idx": "return",
                "name": "Zwrot środków"
            },
            {
                "idx": "exchange",
                "name": "Wymiana produktów"
            },
            {
                "idx": "voucher",
                "name": "Voucher"
            }
        ],
        "return_methods": [
            {
                "idx": "send_myself",
                "name": "Sam wyślę produkt"
            }
        ]
    }
}
```
## POST Create order return
Wymaga autoryzacji użytkownika oraz podania klucza X-API-KEY.
Pozwala na utworzenie zwrotu. 
`POST /api/returns/V1/<channel_idx>/returns/returns`:

BODY:
```json
{
    "order_id": "{{order_id}}",
    "returned_items": [
        {
            "sku": "MAX-36-Czarny",
            "quantity": "1"
        },
        {
            "sku": "MAX-40-Czarny",
            "quantity": "1"
        },
        {
            "sku": "MAX-38-Czarny",
            "quantity": "3"
        }
    ],
    "return_method": "send_myself", // idx metody
    "return_solution": "return", // idx rozwiązania
    "comment": "testowy komentarz",
    "email": "customer@example.com",
    "bank_account_number": "12345678912345678912345678"
}
```

RESPONSE:
```json
{
    "meta": {
        "status": "OK",
        "message": "",
        "messages": [],
        "regional": {
            "language": null,
            "currency": null,
            "country": null
        }
    },
    "data": {
        "status": "open",
        "return_method": "",
        "return_solution": "Sam wyślę produkt",
        "comment": "testowy komentarz",
        "email": "customer@example.com",
        "bank_account_number": "12345678912345678912345678",
        "returned_items": [
            {
                "sku": "MAX-36-Czarny",
                "quantity": 1
            }
        ],
        "order_id": "efcd08b4-d229-4c17-94f4-04083e0a338f",
        "return_id": "e7644e2c-662c-4963-a553-6da9288ee57e"
    }
}
```


## POST Add attachment to return
Wymaga autoryzacji użytkownika oraz podania klucza X-API-KEY. Wymaga content-type: multipart/form-data. 
Pozwala na dodanie załącznika do zwrotu.
`POST /api/returns/V1/<channel_idx>/returns/<return_id>/`:

curl:
```text
curl --location --request POST '<url>/api/returns/V1/test-channel-pl/returns/4c575741-1093-4cfb-bafe-838bafe60b03'
--header 'Authorization: Bearer xyz'
--header 'Content-Type: multipart/form-data' 
--header 'X-API-KEY: xyz' 
--form 'attachment=@"/home/mat/Pobrane/debug-all.log"
```

## PATCH Modify details of return
Wymaga autoryzacji użytkownika oraz podania klucza X-API-KEY.
Można zmodyfikować za pomocą tego endpointu jakiekolwiek pole w zwrocie.
`PATCH /api/returns/V1/<channel_idx>/returns/<return_id>/`:

BODY:
```json
{
    "returned_items": [
        {
            "sku": "MAX-36-Czarny",
            "quantity": "1"
        },
        {
            "sku": "MAX-40-Czarny",
            "quantity": "1"
        },
        {
            "sku": "MAX-38-Czarny",
            "quantity": "3"
        }
    ],
    "return_method": "send_myself", // idx metody
    "return_solution": "return", // idx rozwiązania
    "comment": "testowy komentarz",
    "email": "customer@example.com",
    "bank_account_number": "12345678912345678912345678"
}
```

RESPONSE:
```json
{
    "meta": {
        "status": "OK",
        "message": "",
        "messages": [],
        "regional": {
            "language": null,
            "currency": null,
            "country": null
        }
    },
    "data": {
        "status": "open",
        "return_method": "Sam wyślę produkt",
        "return_solution": "Zwrot środków",
        "comment": "testowy komentarz",
        "email": "customer@example.com",
        "bank_account_number": "12345678912345678912345678",
        "returned_items": [
            {
                "sku": "MAX-36-Czarny",
                "quantity": 3
            }
        ],
        "order_id": "efcd08b4-d229-4c17-94f4-04083e0a338f",
        "return_id": "3f2a6ce1-4f63-40d1-91cd-dd5cc46f4d1b"
    }
}
```


## GET Listing of returns
Wymaga autoryzacji użytkownika oraz podania klucza X-API-KEY.
Zwraca listę zwrotów. Można sortować po dacie utworzenia, paginować.
`GET /api/returns/V1/<channel_idx>/returns/?sort={"created_at": "ASC"}&page=2&limit=1`:

```json
{
    "meta": {
        "status": "OK",
        "message": "",
        "messages": [],
        "regional": {
            "language": null,
            "currency": null,
            "country": null
        }
    },
    "data": [
        {
            "return_id": "7ce7739f-d673-4ee5-8bc0-91b3f31bfab1",
            "created_at": "24/10/2023",
            "order_pretty_id": "1000000004",
            "status": "open",
            "attachments": [
                {
                    "file_id": 2,
                    "name": "nazwa.pdf",
                    "path": "/returns/efcd08b4-d229-4c17-94f4-04083e0a338f/file/2/customer/5cba427c-ddf3-4333-9e22-561d476cd0ee"
                }
            ]
        }
    ],
    "pagination": {
        "page": 2,
        "limit": 1,
        "pages": 2,
        "records": 2
    }
}
```

## GET Details of return
Wymaga autoryzacji użytkownika oraz podania klucza X-API-KEY.
Zwraca szczegóły zwrotu.
`GET /api/returns/V1/<channel_idx>/returns/<return_id>/`:
```json
{
    "meta": {
        "status": "OK",
        "message": "",
        "messages": [],
        "regional": {
            "language": null,
            "currency": null,
            "country": null
        }
    },
    "data": {
        "return_id": "7ce7739f-d673-4ee5-8bc0-91b3f31bfab1",
        "created_at": "24/10/2023",
        "order_pretty_id": "1000000004",
        "status": "open",
        "address": {
            "email": "customer@example.com",
            "firstname": "Test",
            "lastname": "Testowicz",
            "country_code": "PL",
            "city": "Warsaw",
            "postcode": "00-000",
            "street": "test street 89",
            "dialling_code": "+48",
            "telephone": "500500500",
            "company": ""
        },
        "return_solution": "Zwrot środków",
        "return_method": "Sam wyślę produkt",
        "returned_items": [
            {
                "sku": "MAX-36-Czarny",
                "quantity": 1
            }
        ]
    }
}
```

## GET Return attachment
Pozwala na pobranie załącznika (pliku) zwrotu. Plik jest w body odpowiedzi, przeglądarka powinna rozpoznać to jako pobranie pliku. Nie potrzebny jest api-key.
`GET /api/returns/V1/<channel_idx>/returns/<return_id>/file/<file_id>/customer/<customer_id>`:

curl:
```text
curl --location --request GET '[PUBLIC_URL]/api/returns/V1/test-channel-pl/returns/37e06db6-a9d3-4399-920a-030f887b05f2/file/1/customer/5cba427c-ddf3-4333-9e22-561d476cd0ee' \
--header 'Content-Type: application/octet-stream' \
--header 'Content-Disposition: attachment; filename=<file_name>' \
--header 'x-filename: <file_name>' \
--header 'Access-Control-Expose-Headers: x-filename'
```