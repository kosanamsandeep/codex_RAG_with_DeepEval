from __future__ import annotations

import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

from rag_practice.adapters.container import build_ingest_pipeline, build_query_pipeline, load_env


def initialize_session_state():
    """Initialize Streamlit session state for chat history and index."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "ingest" not in st.session_state:
        st.session_state.ingest = None
    if "query_uc" not in st.session_state:
        st.session_state.query_uc = None
    if "citations" not in st.session_state:
        st.session_state.citations = {}


def load_index(persist_dir: str, no_persist: bool) -> tuple:
    """Load or build the index and return ingest + query pipeline."""
    ingest = build_ingest_pipeline()
    persist_path = Path(persist_dir)
    index_path = persist_path / "faiss.index"
    meta_path = persist_path / "chunks.pkl"

    if not no_persist:
        try:
            ingest.index.load(index_path, meta_path)  # type: ignore[attr-defined]
        except Exception as e:
            st.warning(f"Could not load persisted index: {e}. Building fresh index...")

    # Check if index is empty and needs ingestion
    if no_persist or not getattr(ingest.index, "_index", None) or getattr(ingest.index, "_index").ntotal == 0:  # type: ignore[attr-defined]
        with st.spinner("Building vector index from documents..."):
            ingest.execute()
        if not no_persist:
            try:
                ingest.index.save(index_path, meta_path)  # type: ignore[attr-defined]
            except Exception as e:
                st.warning(f"Could not save index: {e}")

    query_uc = build_query_pipeline(index=ingest.index)  # type: ignore[arg-type]
    return ingest, query_uc


def format_answer_with_citations(answer: str, retrieved_chunks: list) -> tuple[str, dict]:
    """
    Format answer with inline citations [1], [2], etc.
    Returns formatted answer and citation mapping.
    """
    citations = {}
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        citations[idx] = {
            "chunk_id": chunk.chunk_id,
            "text": chunk.text[:300] + "..." if len(chunk.text) > 300 else chunk.text,
            "source": chunk.metadata.source_id,
            "page": chunk.metadata.page,
            "score": chunk.score,
        }

    # Simple approach: append citations list after answer
    formatted = answer + "\n\n---\n"
    return formatted, citations


def display_citations(citations: dict):
    """Display citations in an expandable format."""
    st.subheader("📚 Sources")
    for idx, citation in citations.items():
        with st.expander(f"[{idx}] {citation['source']} - Page {citation['page']} (Score: {citation['score']:.3f})"):
            st.write(f"**Chunk ID**: {citation['chunk_id']}")
            st.write(f"**Text**: {citation['text']}")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Similarity Score", f"{citation['score']:.3f}")
            with col2:
                st.metric("Source Page", citation['page'])
            # Optional: link to document
            doc_path = Path("data/processed") / f"{citation['source']}"
            if doc_path.exists():
                st.info(f"📄 Source: {doc_path}")


def main():
    st.set_page_config(page_title="RAG Chat Engine", layout="wide")
    st.title("🤖 RAG Chat Engine")
    st.markdown("Ask questions about your documents. Answers include citations you can click for context.")

    # Load environment
    load_env()
    from dotenv import load_dotenv as load_env_dotenv
    load_env_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        st.error("❌ OPENAI_API_KEY not set. Add it to .env file.")
        st.stop()

    # Initialize session
    initialize_session_state()

    # Sidebar: Configuration
    with st.sidebar:
        st.header("⚙️ Settings")
        persist_dir = st.text_input("Index directory", value="data/index")
        no_persist = st.checkbox("Force fresh ingest (no cache)", value=False)
        top_k = st.slider("Number of sources to retrieve", 1, 10, 3)
        
        # Similarity threshold filtering
        st.subheader("🎯 Filtering")
        similarity_threshold = st.slider(
            "Similarity Threshold",
            min_value=0.0,
            max_value=3.0,
            value=2.5,
            step=0.1,
            help="FAISS L2 distance. Lower = more similar. Filter results above this threshold."
        )
        
        # Metadata filtering
        with st.expander("📋 Metadata Filters (optional)"):
            filter_source = st.text_input("Filter by source (e.g., 'basic-text.pdf')", value="")
            filter_page_min = st.number_input("Min page", value=0, min_value=0)
            filter_page_max = st.number_input("Max page", value=999, min_value=0)
            filter_chunk_type = st.selectbox("Chunk type", ["All", "Text", "Table"])
        
        show_raw_chunks = st.checkbox("Show raw retrieved chunks", value=False)

        if st.button("🔄 Reload Index"):
            st.session_state.ingest = None
            st.session_state.query_uc = None
            st.rerun()

    # Load index on first run or if settings change
    if st.session_state.ingest is None or st.session_state.query_uc is None:
        with st.spinner("Loading vector index..."):
            ingest, query_uc = load_index(persist_dir, no_persist)
            st.session_state.ingest = ingest
            st.session_state.query_uc = query_uc
        st.success("✅ Index loaded!")

    # Chat interface
    st.subheader("💬 Chat")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "citations" in message:
                display_citations(message["citations"])

    # User input
    if prompt := st.chat_input("Ask a question about your documents..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Retrieve and generate answer
        with st.spinner("🔍 Searching documents..."):
            retrieved = st.session_state.query_uc.execute(prompt, top_k=top_k)
        
        # Apply filtering
        retrieved_filtered = []
        for chunk in retrieved:
            # Filter by similarity threshold
            if chunk.score > similarity_threshold:
                continue
            
            # Filter by source
            if filter_source and filter_source not in chunk.metadata.source_id:
                continue
            
            # Filter by page range
            if not (filter_page_min <= chunk.metadata.page <= filter_page_max):
                continue
            
            # Filter by chunk type
            chunk_type = chunk.metadata.extra.get('chunk_type', 'text')
            if filter_chunk_type != "All":
                if (filter_chunk_type == "Text" and chunk_type != "text") or \
                   (filter_chunk_type == "Table" and chunk_type != "table"):
                    continue
            
            retrieved_filtered.append(chunk)
        
        retrieved = retrieved_filtered if retrieved_filtered else retrieved

        if not retrieved:
            answer = "❌ No relevant documents found after filtering. Please adjust your filters or try a different question."
            citations = {}
        else:
            # Display result count
            st.info(f"📊 Retrieved {len(retrieved)} results (filtered from {len(st.session_state.query_uc.execute(prompt, top_k=top_k))})")
            
            # Display raw chunks if requested
            if show_raw_chunks:
                with st.expander("📋 Raw Retrieved Chunks"):
                    for idx, chunk in enumerate(retrieved, start=1):
                        st.write(f"**Chunk {idx}**: {chunk.chunk_id}")
                        st.write(chunk.text[:200] + "..." if chunk.text else "[Table chunk - no text]")
                        st.write(f"Page {chunk.metadata.page} | Score: {chunk.score:.3f} | Type: {chunk.metadata.extra.get('chunk_type')}")
                        st.divider()

            # Generate answer with OpenAI
            with st.spinner("✍️ Generating answer..."):
                try:
                    from langchain_openai import ChatOpenAI
                    from langchain_core.messages import SystemMessage, HumanMessage

                    llm = ChatOpenAI(model="gpt-4", temperature=0.7)
                    context = "\n\n".join([f"[Source {i}]: {chunk.text}" for i, chunk in enumerate(retrieved, start=1)])
                    system_msg = SystemMessage(content="You are a helpful assistant answering questions based on provided documents. Use citations [1], [2], etc. when referencing specific sources.")
                    user_msg = HumanMessage(content=f"Question: {prompt}\n\nDocuments:\n{context}")
                    response = llm.invoke([system_msg, user_msg])
                    answer = response.content
                except Exception as e:
                    answer = f"Error generating answer: {e}"

            # Format answer with citations
            formatted_answer, citations = format_answer_with_citations(answer, retrieved)

        # Add to chat history
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "citations": citations,
        })

        # Display latest response
        with st.chat_message("assistant"):
            st.markdown(answer)
            if citations:
                display_citations(citations)


if __name__ == "__main__":
    main()
