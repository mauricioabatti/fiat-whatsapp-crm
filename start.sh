#!/bin/sh

echo "A iniciar a aplicação na porta: ${PORT:-8080}"
gunicorn wsgi:app --bind 0.0.0.0:${PORT:-8080} --log-level=debug

