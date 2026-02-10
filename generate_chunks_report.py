import pickle

# Load chunks
with open('data/index/chunks.pkl', 'rb') as f:
    chunks = pickle.load(f)

# Open output file
with open('chunks_output.txt', 'w', encoding='utf-8') as out:
    out.write("=" * 100 + "\n")
    out.write("DOCUMENT CHUNKS ANALYSIS\n")
    out.write("=" * 100 + "\n\n")
    
    out.write(f"Total chunks: {len(chunks)}\n\n")
    
    # Group chunks by source
    sources = {}
    for chunk in chunks:
        src = chunk.metadata.source_id
        if src not in sources:
            sources[src] = []
        sources[src].append(chunk)
    
    for source_id, source_chunks in sources.items():
        out.write(f"\n{'=' * 100}\n")
        out.write(f"SOURCE: {source_id}\n")
        out.write(f"{'=' * 100}\n")
        out.write(f"Total chunks from this source: {len(source_chunks)}\n\n")
        
        for i, chunk in enumerate(source_chunks, 1):
            out.write(f"\n{'-' * 100}\n")
            out.write(f"CHUNK #{i}\n")
            out.write(f"{'-' * 100}\n")
            out.write(f"Chunk ID: {chunk.chunk_id}\n")
            out.write(f"Page: {chunk.metadata.page}\n")
            out.write(f"Section: {chunk.metadata.section}\n")
            out.write(f"Image References: {chunk.metadata.image_refs}\n")
            out.write(f"Extra Metadata: {chunk.metadata.extra}\n")
            out.write(f"\nText Content:\n")
            out.write(f"{chunk.text}\n")
    
    out.write(f"\n\n{'=' * 100}\n")
    out.write("END OF CHUNKS REPORT\n")
    out.write(f"{'=' * 100}\n")

print("✓ Chunks output saved to: chunks_output.txt")
