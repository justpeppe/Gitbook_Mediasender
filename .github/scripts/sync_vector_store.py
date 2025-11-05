import os
import glob
from openai import OpenAI

# --- 1. Impostazioni Iniziali ---
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    vector_store_id = os.environ.get("VECTOR_STORE_ID")

    if not vector_store_id:
        raise ValueError("Errore: VECTOR_STORE_ID non è impostato nei secrets.")
    if not client.api_key:
        raise ValueError("Errore: OPENAI_API_KEY non è impostato nei secrets.")

    print(f"--- Avvio sincronizzazione per Vector Store: {vector_store_id} ---")

except Exception as e:
    print(e)
    exit(1)


# --- 2. Pulizia del Vector Store (Svuotamento) ---
print("Recupero i file esistenti nel Vector Store...")
try:
    # Prendo tutti i file associati allo store
    vector_files = client.vector_stores.files.list(vector_store_id=vector_store_id)
    file_ids_to_delete = [file.id for file in vector_files.data]
    
    if not file_ids_to_delete:
        print("Nessun file trovato nel Vector Store. Salto la pulizia.")
    else:
        print(f"Trovati {len(file_ids_to_delete)} file da rimuovere...")
        for file_id in file_ids_to_delete:
            try:
                # 1. Rimuovo l'associazione dal Vector Store
                client.vector_stores.files.delete(
                    vector_store_id=vector_store_id, 
                    file_id=file_id
                )
                # 2. Elimino il file da OpenAI (opzionale ma pulito)
                client.files.delete(file_id=file_id)
                print(f"Rimosso e eliminato file: {file_id}")
            except Exception as e:
                # Ignoro errori se il file fosse già stato cancellato
                print(f"Errore minore durante la rimozione del file {file_id}: {e}")
        print("Pulizia completata.")

except Exception as e:
    print(f"Errore grave durante la pulizia dei file: {e}")
    # Decidiamo di non continuare se la pulizia fallisce
    exit(1)


# --- 3. Ricerca dei file .md nel repository ---
# Cerca in tutte le sottocartelle (**) per qualsiasi file che finisce in .md
markdown_files = glob.glob("**/*.md", recursive=True)

if not markdown_files:
    print("Nessun file .md trovato nel repository. Sincronizzazione terminata.")
    exit()

print(f"Trovati {len(markdown_files)} file .md da caricare.")


# --- 4. Caricamento dei nuovi file su OpenAI ---
uploaded_file_ids = []
for file_path in markdown_files:
    # Ignoriamo file che potrebbero essere parte del setup, come README.md
    if file_path.startswith('.github/') or file_path == 'README.md':
        print(f"Ignoro file: {file_path}")
        continue

    print(f"Caricamento di: {file_path}")
    try:
        with open(file_path, "rb") as f:
            # Carica il file su OpenAI
            response = client.files.create(file=f, purpose="assistants")
            uploaded_file_ids.append(response.id)
            print(f"  -> Caricato come File ID: {response.id}")
    except Exception as e:
        print(f"Errore durante il caricamento di {file_path}: {e}")

# --- 5. Aggiunta dei file al Vector Store (in blocco) ---
if uploaded_file_ids:
    print(f"Aggiunta di {len(uploaded_file_ids)} file al Vector Store (in batch)...")
    try:
        # Usiamo il "file_batches" per aggiungere tutti i file in una sola chiamata
        batch = client.vector_stores.file_batches.create(
            vector_store_id=vector_store_id,
            file_ids=uploaded_file_ids
        )
        print(f"Batch creato: {batch.id} (Stato: {batch.status})")
        print("Il Vector Store si aggiornerà in background.")
    except Exception as e:
        print(f"Errore grave durante la creazione del batch: {e}")
        exit(1)

print("--- Sincronizzazione completata! ---")