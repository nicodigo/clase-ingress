import os

import httpx
from nicegui import ui

USERS_API_URL = os.environ.get("USERS_API_URL", "http://localhost:8000")
API_USERS = f"{USERS_API_URL}/users/"


@ui.page("/")
async def index():
    rows: list[dict] = []
    client = httpx.AsyncClient(follow_redirects=True)

    async def fetch():
        try:
            resp = await client.get(API_USERS)
            resp.raise_for_status()
            rows.clear()
            rows.extend(resp.json())
            tbl.update()
        except Exception as e:
            ui.notify(f"Error fetching users: {e}", type="negative")

    async def add_user():
        try:
            resp = await client.post(
                API_USERS,
                json={"name": nm.value, "email": em.value},
            )
            resp.raise_for_status()
            ui.notify("User created", type="positive")
            nm.value = ""
            em.value = ""
            await fetch()
        except Exception as e:
            ui.notify(f"Error creating user: {e}", type="negative")

    async def remove(uid: int):
        try:
            resp = await client.delete(f"{API_USERS}{uid}")
            resp.raise_for_status()
            ui.notify("User deleted", type="positive")
            await fetch()
        except Exception as e:
            ui.notify(f"Error deleting user: {e}", type="negative")

    columns = [
        {"name": "id", "label": "ID", "field": "id"},
        {"name": "name", "label": "Name", "field": "name"},
        {"name": "email", "label": "Email", "field": "email"},
        {"name": "created_at", "label": "Created At", "field": "created_at"},
        {"name": "actions", "label": "Actions", "field": "id"},
    ]

    ui.label("Users Management").classes("text-2xl font-bold mb-4")

    with ui.card().classes("mb-4"):
        ui.label("Create User").classes("text-lg font-semibold mb-2")
        with ui.row().classes("gap-2 items-end"):
            nm = ui.input("Name")
            em = ui.input("Email")
            ui.button("Create", on_click=add_user)

    with ui.card():
        with ui.row().classes("justify-between items-center mb-2"):
            ui.label("Users").classes("text-lg font-semibold")
            ui.button("Refresh", on_click=fetch, icon="refresh")
        tbl = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")
        tbl.add_slot(
            "body-cell-actions",
            """
            <q-td :props="props">
                <q-btn color="negative" icon="delete" dense flat
                    @click="$parent.$parent.$emit('del', props.row.id)" />
            </q-td>
            """,
        )
        tbl.on("del", lambda e: remove(e.args[0] if isinstance(e.args, (list, tuple)) else e.args))

    await fetch()


ui.run(host="0.0.0.0", port=8080, title="User Management")
