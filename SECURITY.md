# Seguridad de FisoLógico

## Comunicación responsable

Si detectas una vulnerabilidad o una posible exposición de información, comunícala de forma privada a `hola@elfisiologico.com`. No incluyas datos de salud, datos personales de terceros ni credenciales en una incidencia pública.

## Alcance y datos sensibles

- El repositorio y el artefacto público no deben contener secretos, contraseñas, claves privadas, volcados de bases de datos ni documentación de trabajo interna.
- Las claves publicables de clientes web no sustituyen los controles de autorización del servidor.
- Los formularios públicos no deben solicitar información clínica ni datos de salud salvo que exista una necesidad validada y una infraestructura específicamente preparada para ello.
- Los datos de pago se gestionan en Stripe; FisoLógico no debe recibir ni almacenar números de tarjeta.

## Validación antes de publicar

Ejecuta:

```bash
python3 scripts/security_audit.py
python3 scripts/build_public_site.py --output output/public-site
```

El despliegue de GitHub Pages repite estas comprobaciones y solo publica el artefacto generado mediante lista blanca.
