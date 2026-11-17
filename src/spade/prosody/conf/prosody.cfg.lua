-- Prosody configuration file
admins = { "admin@serverhello" }

-- Global settings
network_backend = "epoll"

log = {
    -- TYLKO błędy  na konsolę (docker logs)
    { levels = { "error" }, to = "console" };

    -- wszystko ważniejsze do osobnego pliku
    { levels = { "info", "warn", "error" }, to = "file", filename = "/var/log/prosody/prosody.err" };
}

modules_enabled = {
    "roster"; -- Allow users to have a roster
    "saslauth"; -- Authentication for clients and servers
    "tls"; -- Enable secure connections
    "dialback"; -- Server-to-server dialback
    "disco"; -- Service discovery
    "carbons"; -- Keep messages synced across devices
    "mam"; -- Store and access message archives
	"register";
}

allow_registration = true -- Enable users to self-register

ssl = {
    certificate = "/etc/prosody/certs/localhost.crt";
    key = "/etc/prosody/certs/localhost.key";
}

VirtualHost "serverhello"
    enabled = true
    authentication = "internal_plain"  -- ZAMIANA z "anonymous"
