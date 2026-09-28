"""Torna bonding_consentrecord append-only a nivel de banco: qualquer UPDATE ou
DELETE e rejeitado por uma trigger, mesmo que executado fora do Django ORM
(psql direto, outro serviço, um superusuario mal-intencionado sem acesso ao
codigo da aplicacao). Isso complementa (nao substitui) o controle de
aplicacao: bonding.services.consent.record_consent() e a unica funcao que
deve criar registros, e o model nunca expoe update()/delete() com essa
finalidade.

Esta trigger assume PostgreSQL (unico engine suportado pelo projeto, ver
setup/settings.py DATABASES via dj_database_url)."""

from django.db import migrations

CREATE_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION bonding_reject_consent_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'bonding_consentrecord e append-only: operacao % nao e permitida (id=%)', TG_OP, OLD.id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER consent_record_no_update_delete
BEFORE UPDATE OR DELETE ON bonding_consentrecord
FOR EACH ROW EXECUTE FUNCTION bonding_reject_consent_mutation();
"""

DROP_TRIGGER_SQL = """
DROP TRIGGER IF EXISTS consent_record_no_update_delete ON bonding_consentrecord;
DROP FUNCTION IF EXISTS bonding_reject_consent_mutation();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("bonding", "0018_legal_consent_models"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_TRIGGER_SQL, reverse_sql=DROP_TRIGGER_SQL),
    ]
