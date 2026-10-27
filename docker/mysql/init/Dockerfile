FROM mysql:8.4

COPY 01-schema.sql /docker-entrypoint-initdb.d/01-schema.sql
COPY 02-datos-iniciales.sql /docker-entrypoint-initdb.d/02-datos-iniciales.sql
