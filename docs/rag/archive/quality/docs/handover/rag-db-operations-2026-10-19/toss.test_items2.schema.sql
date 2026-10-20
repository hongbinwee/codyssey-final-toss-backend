--
-- PostgreSQL database dump
--

\restrict w54po7EptyhjoTOuFWzpPpCdAJjcETIobixJP36WmxOuPkiVvB98f6FjEFdxhCB

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
-- Name: test_items2; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA test_items2;


--
-- Name: SCHEMA test_items2; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA test_items2 IS 'Shopping Brain v6.1 review-refined CANDIDATE, imported 2026-10-19. Original IDs and REAL/SYNTHETIC provenance preserved.';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: product_variants; Type: TABLE; Schema: test_items2; Owner: -
--

CREATE TABLE test_items2.product_variants (
    id text NOT NULL,
    product_id text NOT NULL,
    option_values_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    spec_overrides_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    unit_price_won integer NOT NULL,
    stock_qty integer NOT NULL,
    active boolean DEFAULT true NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    CONSTRAINT product_variants_stock_qty_check CHECK ((stock_qty >= 0)),
    CONSTRAINT product_variants_unit_price_won_check CHECK ((unit_price_won >= 0)),
    CONSTRAINT product_variants_version_check CHECK ((version >= 1))
);


--
-- Name: products; Type: TABLE; Schema: test_items2; Owner: -
--

CREATE TABLE test_items2.products (
    id text NOT NULL,
    name text NOT NULL,
    brand text NOT NULL,
    category text NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    image_urls jsonb DEFAULT '[]'::jsonb NOT NULL,
    specs_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    active boolean DEFAULT true NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    CONSTRAINT products_version_check CHECK ((version >= 1))
);


--
-- Name: reviews; Type: TABLE; Schema: test_items2; Owner: -
--

CREATE TABLE test_items2.reviews (
    id text NOT NULL,
    product_id text NOT NULL,
    variant_id text,
    rating integer NOT NULL,
    body text NOT NULL,
    source_kind text NOT NULL,
    source_ref text DEFAULT ''::text NOT NULL,
    written_at timestamp with time zone NOT NULL,
    source_option_label text,
    CONSTRAINT reviews_rating_check CHECK (((rating >= 1) AND (rating <= 5))),
    CONSTRAINT reviews_source_kind_check CHECK ((source_kind = ANY (ARRAY['REAL'::text, 'SYNTHETIC'::text])))
);


--
-- Name: COLUMN reviews.source_option_label; Type: COMMENT; Schema: test_items2; Owner: -
--

COMMENT ON COLUMN test_items2.reviews.source_option_label IS 'Original source option label from supplied v6.1 dataset.';


--
-- Name: product_variants product_variants_pkey; Type: CONSTRAINT; Schema: test_items2; Owner: -
--

ALTER TABLE ONLY test_items2.product_variants
    ADD CONSTRAINT product_variants_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: test_items2; Owner: -
--

ALTER TABLE ONLY test_items2.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: test_items2; Owner: -
--

ALTER TABLE ONLY test_items2.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: product_variants_product_id_id_idx; Type: INDEX; Schema: test_items2; Owner: -
--

CREATE UNIQUE INDEX product_variants_product_id_id_idx ON test_items2.product_variants USING btree (product_id, id);


--
-- Name: product_variants_product_id_idx; Type: INDEX; Schema: test_items2; Owner: -
--

CREATE INDEX product_variants_product_id_idx ON test_items2.product_variants USING btree (product_id);


--
-- Name: reviews_product_id_idx; Type: INDEX; Schema: test_items2; Owner: -
--

CREATE INDEX reviews_product_id_idx ON test_items2.reviews USING btree (product_id);


--
-- Name: product_variants product_variants_product_id_fkey; Type: FK CONSTRAINT; Schema: test_items2; Owner: -
--

ALTER TABLE ONLY test_items2.product_variants
    ADD CONSTRAINT product_variants_product_id_fkey FOREIGN KEY (product_id) REFERENCES test_items2.products(id);


--
-- Name: reviews reviews_product_id_fkey; Type: FK CONSTRAINT; Schema: test_items2; Owner: -
--

ALTER TABLE ONLY test_items2.reviews
    ADD CONSTRAINT reviews_product_id_fkey FOREIGN KEY (product_id) REFERENCES test_items2.products(id);


--
-- Name: reviews reviews_product_id_variant_id_fkey; Type: FK CONSTRAINT; Schema: test_items2; Owner: -
--

ALTER TABLE ONLY test_items2.reviews
    ADD CONSTRAINT reviews_product_id_variant_id_fkey FOREIGN KEY (product_id, variant_id) REFERENCES test_items2.product_variants(product_id, id);


--
-- PostgreSQL database dump complete
--

\unrestrict w54po7EptyhjoTOuFWzpPpCdAJjcETIobixJP36WmxOuPkiVvB98f6FjEFdxhCB

