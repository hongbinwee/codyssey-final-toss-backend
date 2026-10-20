--
-- PostgreSQL database dump
--

\restrict 8uECPwXCfQdxo4vbUfXeMUobN2QI94f7l2GAYGuEgxtrJv4Hg8vdRvsIoiCJ1fN

-- Dumped from database version 18.6 (Debian 18.6-1.pgdg13+2)
-- Dumped by pg_dump version 18.6 (Debian 18.6-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: rag; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA rag;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: evidence_chunks; Type: TABLE; Schema: rag; Owner: -
--

CREATE TABLE rag.evidence_chunks (
    run_id uuid NOT NULL,
    chunk_key text NOT NULL,
    chunk_id text NOT NULL,
    dataset_version text NOT NULL,
    category text NOT NULL,
    product_id text NOT NULL,
    source_type text NOT NULL,
    source_id text NOT NULL,
    source_field text NOT NULL,
    start_offset integer NOT NULL,
    end_offset integer NOT NULL,
    evidence_text text NOT NULL,
    embedding_text text NOT NULL,
    source_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    embedding public.vector(384) NOT NULL,
    embedding_model text NOT NULL,
    chunker_version text NOT NULL,
    CONSTRAINT evidence_chunks_check CHECK ((end_offset > start_offset)),
    CONSTRAINT evidence_chunks_check1 CHECK ((char_length(evidence_text) = (end_offset - start_offset))),
    CONSTRAINT evidence_chunks_check2 CHECK (((source_type <> 'product'::text) OR (source_id = product_id))),
    CONSTRAINT evidence_chunks_source_field_check CHECK ((source_field ~~ '/%'::text)),
    CONSTRAINT evidence_chunks_source_type_check CHECK ((source_type = ANY (ARRAY['product'::text, 'review'::text]))),
    CONSTRAINT evidence_chunks_start_offset_check CHECK ((start_offset >= 0))
);


--
-- Name: index_profiles; Type: TABLE; Schema: rag; Owner: -
--

CREATE TABLE rag.index_profiles (
    profile_name text NOT NULL,
    active_run_id uuid NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: index_runs; Type: TABLE; Schema: rag; Owner: -
--

CREATE TABLE rag.index_runs (
    run_id uuid NOT NULL,
    dataset_version text NOT NULL,
    embedding_model text NOT NULL,
    chunker_version text NOT NULL,
    category_policy_version text DEFAULT 'legacy'::text NOT NULL,
    status text NOT NULL,
    counts jsonb DEFAULT '{}'::jsonb NOT NULL,
    error_code text,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    profile_name text NOT NULL,
    CONSTRAINT index_runs_status_check CHECK ((status = ANY (ARRAY['building'::text, 'active'::text, 'superseded'::text, 'failed'::text])))
);


--
-- Name: indexed_products; Type: TABLE; Schema: rag; Owner: -
--

CREATE TABLE rag.indexed_products (
    run_id uuid NOT NULL,
    dataset_version text NOT NULL,
    category text NOT NULL,
    product_id text NOT NULL,
    product_payload jsonb NOT NULL,
    price_amount numeric,
    price_currency text
);


--
-- Name: quarantined_products; Type: TABLE; Schema: rag; Owner: -
--

CREATE TABLE rag.quarantined_products (
    run_id uuid NOT NULL,
    dataset_version text NOT NULL,
    category text NOT NULL,
    product_id text NOT NULL,
    reason_code text NOT NULL,
    policy_version text NOT NULL,
    product_title text,
    main_category text,
    categories jsonb DEFAULT '[]'::jsonb NOT NULL,
    type_signals jsonb DEFAULT '[]'::jsonb NOT NULL,
    review_status text DEFAULT 'pending_review'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT quarantined_products_review_status_check CHECK ((review_status = ANY (ARRAY['pending_review'::text, 'confirmed'::text, 'rejected'::text])))
);


--
-- Name: evidence_chunks evidence_chunks_chunk_key_key; Type: CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.evidence_chunks
    ADD CONSTRAINT evidence_chunks_chunk_key_key UNIQUE (chunk_key);


--
-- Name: evidence_chunks evidence_chunks_pkey; Type: CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.evidence_chunks
    ADD CONSTRAINT evidence_chunks_pkey PRIMARY KEY (run_id, chunk_id);


--
-- Name: index_profiles index_profiles_pkey; Type: CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.index_profiles
    ADD CONSTRAINT index_profiles_pkey PRIMARY KEY (profile_name);


--
-- Name: index_runs index_runs_pkey; Type: CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.index_runs
    ADD CONSTRAINT index_runs_pkey PRIMARY KEY (run_id);


--
-- Name: index_runs index_runs_run_id_dataset_version_key; Type: CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.index_runs
    ADD CONSTRAINT index_runs_run_id_dataset_version_key UNIQUE (run_id, dataset_version);


--
-- Name: indexed_products indexed_products_pkey; Type: CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.indexed_products
    ADD CONSTRAINT indexed_products_pkey PRIMARY KEY (run_id, category, product_id);


--
-- Name: indexed_products indexed_products_run_id_dataset_version_category_product_id_key; Type: CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.indexed_products
    ADD CONSTRAINT indexed_products_run_id_dataset_version_category_product_id_key UNIQUE (run_id, dataset_version, category, product_id);


--
-- Name: quarantined_products quarantined_products_pkey; Type: CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.quarantined_products
    ADD CONSTRAINT quarantined_products_pkey PRIMARY KEY (run_id, category, product_id);


--
-- Name: evidence_chunks_run_source_idx; Type: INDEX; Schema: rag; Owner: -
--

CREATE INDEX evidence_chunks_run_source_idx ON rag.evidence_chunks USING btree (run_id, category, product_id, source_type);


--
-- Name: evidence_chunks_search_idx; Type: INDEX; Schema: rag; Owner: -
--

CREATE INDEX evidence_chunks_search_idx ON rag.evidence_chunks USING paradedb (chunk_key, run_id, embedding_text);


--
-- Name: index_runs_dataset_status_idx; Type: INDEX; Schema: rag; Owner: -
--

CREATE INDEX index_runs_dataset_status_idx ON rag.index_runs USING btree (dataset_version, status);


--
-- Name: index_runs_one_active_per_profile_idx; Type: INDEX; Schema: rag; Owner: -
--

CREATE UNIQUE INDEX index_runs_one_active_per_profile_idx ON rag.index_runs USING btree (profile_name) WHERE (status = 'active'::text);


--
-- Name: index_runs_profile_run_idx; Type: INDEX; Schema: rag; Owner: -
--

CREATE UNIQUE INDEX index_runs_profile_run_idx ON rag.index_runs USING btree (profile_name, run_id);


--
-- Name: indexed_products_run_category_idx; Type: INDEX; Schema: rag; Owner: -
--

CREATE INDEX indexed_products_run_category_idx ON rag.indexed_products USING btree (run_id, category, product_id);


--
-- Name: quarantined_products_review_idx; Type: INDEX; Schema: rag; Owner: -
--

CREATE INDEX quarantined_products_review_idx ON rag.quarantined_products USING btree (review_status, category, product_id);


--
-- Name: evidence_chunks evidence_chunks_run_id_dataset_version_category_product_id_fkey; Type: FK CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.evidence_chunks
    ADD CONSTRAINT evidence_chunks_run_id_dataset_version_category_product_id_fkey FOREIGN KEY (run_id, dataset_version, category, product_id) REFERENCES rag.indexed_products(run_id, dataset_version, category, product_id) ON DELETE CASCADE;


--
-- Name: evidence_chunks evidence_chunks_run_id_fkey; Type: FK CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.evidence_chunks
    ADD CONSTRAINT evidence_chunks_run_id_fkey FOREIGN KEY (run_id) REFERENCES rag.index_runs(run_id) ON DELETE CASCADE;


--
-- Name: index_profiles index_profiles_profile_name_active_run_id_fkey; Type: FK CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.index_profiles
    ADD CONSTRAINT index_profiles_profile_name_active_run_id_fkey FOREIGN KEY (profile_name, active_run_id) REFERENCES rag.index_runs(profile_name, run_id);


--
-- Name: indexed_products indexed_products_run_id_dataset_version_fkey; Type: FK CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.indexed_products
    ADD CONSTRAINT indexed_products_run_id_dataset_version_fkey FOREIGN KEY (run_id, dataset_version) REFERENCES rag.index_runs(run_id, dataset_version) ON DELETE CASCADE;


--
-- Name: indexed_products indexed_products_run_id_fkey; Type: FK CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.indexed_products
    ADD CONSTRAINT indexed_products_run_id_fkey FOREIGN KEY (run_id) REFERENCES rag.index_runs(run_id) ON DELETE CASCADE;


--
-- Name: quarantined_products quarantined_products_run_id_dataset_version_fkey; Type: FK CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.quarantined_products
    ADD CONSTRAINT quarantined_products_run_id_dataset_version_fkey FOREIGN KEY (run_id, dataset_version) REFERENCES rag.index_runs(run_id, dataset_version) ON DELETE CASCADE;


--
-- Name: quarantined_products quarantined_products_run_id_fkey; Type: FK CONSTRAINT; Schema: rag; Owner: -
--

ALTER TABLE ONLY rag.quarantined_products
    ADD CONSTRAINT quarantined_products_run_id_fkey FOREIGN KEY (run_id) REFERENCES rag.index_runs(run_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 8uECPwXCfQdxo4vbUfXeMUobN2QI94f7l2GAYGuEgxtrJv4Hg8vdRvsIoiCJ1fN

