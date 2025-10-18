FROM composer:2.7 as composer_builder

ENV APP_ENV=prod

WORKDIR /app/

COPY composer.json composer.lock ./

RUN composer install --no-dev --no-scripts --no-autoloader \
    && composer dump-autoload --optimize

FROM php:8.3.6-cli as asset_compiler

WORKDIR /app/

# Install necessary PHP extensions for the CLI environment
RUN apt-get update && apt-get install -y \
    libicu-dev \
    && docker-php-ext-install intl  opcache bcmath \
    && rm -rf /var/lib/apt/lists/*

ENV APP_ENV=prod
ENV DATABASE_URL=

COPY --from=composer_builder /app/vendor /app/vendor
COPY config/ /app/config/
COPY src/ /app/src/
COPY public/ /app/public/
COPY bin/ /app/bin/
COPY templates/ /app/templates/
COPY assets/ /app/assets/
COPY importmap.php /app/
COPY symfony.lock composer.json composer.lock /app/

RUN php bin/console importmap:install
RUN php bin/console asset-map:compile --env=prod

FROM php:8.3.6-apache

WORKDIR /var/www/html

# Install necessary OS packages and PHP extensions
RUN apt-get update && apt-get install -y \
    unzip \
    libicu-dev \
    && docker-php-ext-install intl  opcache bcmath \
    && rm -rf /var/lib/apt/lists/*

# Environment variables
ENV APP_ENV=prod
ENV APP_DEBUG=0
ENV LOG_LEVEL=info
ENV PORT=8080
ENV DATABASE_URL=

# Configure PHP production settings (OPcache is critical for performance)
RUN set -ex; \
    { \
        echo "; Cloud Run settings"; \
        echo "memory_limit = -1"; \
        echo "max_execution_time = 0"; \
        echo "upload_max_filesize = 32M"; \
        echo "post_max_size = 32M"; \
        echo "opcache.enable = On"; \
        echo "opcache.validate_timestamps = Off"; \
        echo "opcache.memory_consumption = 32"; \
    } > "$PHP_INI_DIR/conf.d/cloud-run.ini"

RUN mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"

# Configure Apache to listen on the environment port and set the document root
RUN sed -i 's/80/${PORT}/g' /etc/apache2/sites-available/000-default.conf /etc/apache2/ports.conf

ENV APACHE_DOCUMENT_ROOT=/var/www/html/public

RUN sed -ri "s!/var/www/html!${APACHE_DOCUMENT_ROOT}!g" \
    /etc/apache2/sites-available/000-default.conf && \
    sed -ri "s!/var/www/!${APACHE_DOCUMENT_ROOT}/!g" \
    /etc/apache2/apache2.conf /etc/apache2/conf-available/*.conf

RUN a2enmod rewrite

COPY --from=asset_compiler /app/vendor /var/www/html/vendor
COPY --from=asset_compiler /app/config /var/www/html/config
COPY --from=asset_compiler /app/src /var/www/html/src
COPY --from=asset_compiler /app/bin /var/www/html/bin
COPY --from=asset_compiler /app/templates /var/www/html/templates
COPY --from=asset_compiler /app/public /var/www/html/public
COPY --from=asset_compiler /app/symfony.lock /var/www/html/
COPY --from=asset_compiler /app/composer.json /var/www/html/
COPY --from=asset_compiler /app/composer.lock /var/www/html/
COPY --from=asset_compiler /app/importmap.php /var/www/html/

RUN php bin/console cache:clear --env=prod --no-warmup && \
    php bin/console cache:warmup --env=prod && \
    chown -R www-data:www-data /var/www/html

USER www-data

EXPOSE ${PORT}

CMD ["apache2-foreground"]