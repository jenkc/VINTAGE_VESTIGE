from embeddings.generator import generate_embeddings_for_database

def main():
    """Generate embeddings and store in pgvector"""
    print("=" * 60)
    print("VINTAGE VESTIGE - EMBEDDING GENERATION")
    print("=" * 60)

    embeddings_data = generate_embeddings_for_database()

    if not embeddings_data:
        print("No products to process!")
        return

    print(f"\nDone! Generated and stored {len(embeddings_data)} embeddings.")

if __name__ == "__main__":
    main()