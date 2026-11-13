"""ERP evidence and posting guards applied by the schema migration owner."""
DDL=[
"""CREATE FUNCTION erp_posted_stock_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
IF OLD.status = 'posted' AND (TG_OP = 'DELETE' OR (to_jsonb(NEW)-'version') IS DISTINCT FROM (to_jsonb(OLD)-'version')) THEN RAISE EXCEPTION 'posted stock movement is immutable'; END IF; RETURN NEW; END $$""",
"CREATE TRIGGER stock_movements_posted_immutable BEFORE UPDATE OR DELETE ON stock_movements FOR EACH ROW EXECUTE FUNCTION erp_posted_stock_guard()",
"""CREATE FUNCTION erp_receipt_guard() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
IF TG_OP = 'DELETE' OR NEW.amount IS DISTINCT FROM OLD.amount OR NEW.invoice_id IS DISTINCT FROM OLD.invoice_id OR NEW.payer_name IS DISTINCT FROM OLD.payer_name THEN RAISE EXCEPTION 'receipt financial facts are immutable'; END IF; RETURN NEW; END $$""",
"CREATE TRIGGER payment_receipts_financial_immutable BEFORE UPDATE OR DELETE ON payment_receipts FOR EACH ROW EXECUTE FUNCTION erp_receipt_guard()",
"""CREATE FUNCTION erp_balanced_journal() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE entry text; balance numeric; cnt integer; BEGIN
entry := COALESCE(NEW.entry_id,OLD.entry_id); SELECT COALESCE(sum(debit-credit),0),count(*) INTO balance,cnt FROM ledger_lines WHERE entry_id=entry;
IF balance <> 0 OR cnt < 2 THEN RAISE EXCEPTION 'journal must have balanced debit and credit lines'; END IF; RETURN NULL; END $$""",
"CREATE CONSTRAINT TRIGGER ledger_balance AFTER INSERT OR UPDATE OR DELETE ON ledger_lines DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION erp_balanced_journal()",
]
for table in ['ledger_entries','ledger_lines','invoice_adjustments','goods_receipts','remittances','dataset_rows','report_lineage','integration_receipts','report_acknowledgments']:
    DDL.append(f'CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION his_deny_immutable_change()')
