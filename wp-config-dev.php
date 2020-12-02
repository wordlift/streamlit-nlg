<?php
/**
 * The base configuration for WordPress
 *
 * The wp-config.php creation script uses this file during the
 * installation. You don't have to use the web site, you can
 * copy this file to "wp-config.php" and fill in the values.
 *
 * This file contains the following configurations:
 *
 * * MySQL settings
 * * Secret keys
 * * Database table prefix
 * * ABSPATH
 *
 * @link https://codex.wordpress.org/Editing_wp-config.php
 *
 * @package WordPress
 */

@ini_set( 'upload_max_size', '100M' );
@ini_set( 'post_max_size', '100M' );
@ini_set( 'max_execution_time', '300' );

$host_name = getenv( 'COMPOSE_PROJECT_NAME' );
$subdir    = getenv( 'WORDPRESS_SUBDIR' );

define( 'WP_SITEURL', "https://$host_name.www.localhost$subdir" );
define( 'WP_HOME', WP_SITEURL );
define( 'WP_CONTENT_URL', WP_HOME . '/wp-content' );
define( 'WP_CONTENT_DIR', $_SERVER['DOCUMENT_ROOT'] . '/wp-content' );

define( 'WL_ENABLE_MAPPINGS', true );
define( 'WL_ALL_ENTITY_TYPES', true );

# Add support for the reverse proxy.
if ( strpos( $_SERVER['HTTP_X_FORWARDED_PROTO'], 'https' ) !== false ) {
	$_SERVER['HTTPS'] = 'on';
}

if ( isset( $_SERVER['HTTP_X_FORWARDED_HOST'] ) ) {
	$_SERVER['HTTP_HOST'] = $_SERVER['HTTP_X_FORWARDED_HOST'];
}

// ** MySQL settings - You can get this info from your web host ** //
/** The name of the database for WordPress */
define( 'DB_NAME', 'wordpress' );

/** MySQL database username */
define( 'DB_USER', 'wordpress' );

/** MySQL database password */
define( 'DB_PASSWORD', 'password' );

/** MySQL hostname */
define( 'DB_HOST', 'db' );

/** Database Charset to use in creating database tables. */
define( 'DB_CHARSET', 'utf8' );

/** The Database Collate type. Don't change this if in doubt. */
define( 'DB_COLLATE', '' );

/**
 * Authentication Unique Keys and Salts.
 *
 * Change these to different unique phrases!
 * You can generate these using the {@link https://api.wordpress.org/secret-key/1.1/salt/ WordPress.org secret-key service}
 * You can change these at any point in time to invalidate all existing cookies. This will force all users to have to log in again.
 *
 * @since 2.6.0
 */
define( 'AUTH_KEY', '&^i:/FCcRR>y7If;:v9Bc-f|yShT-iPd(cMbv<hn3+00v7c#G]QC~qyO_9FNV.m+' );
define( 'SECURE_AUTH_KEY', 'Nd`rhwI^KK$xeGtzNU0VP+tf<m#2xQ#Q)i)-u#_S61w<%/~J`IB/ 7@lK^Q<5=_b' );
define( 'LOGGED_IN_KEY', 'oW,(uqp_YFI`M0-rO<<LlWm:{$VtxfSYGAD N~[^!SOTc25y!F+g;5jpRT Q/m_(' );
define( 'NONCE_KEY', 'bkKe$BK2fsSmLw4^&U~$vfuRT$sg`G/*%(gUp7oDuhvVOz/M{W7/VmL>um]5`?ZG' );
define( 'AUTH_SALT', '2eK5?|^R e,z:wX@}+k&w/>[fO*iQ79LZ5vz_Q?V+>IP9!D}:{Mck7<k+MUaQ!BW' );
define( 'SECURE_AUTH_SALT', '{6c{M}fV#z|Q=TZ}74C(`t  -6>+1qe!eS!nC,pbPUJu2cchqZzg#%6}WB^{!?A#' );
define( 'LOGGED_IN_SALT', '(x(]3&jU4:V6*U1_2VH`z$30Qlity}ZA8P1y8riURfBs/uwyxzqlX>QE#~w6y#z5' );
define( 'NONCE_SALT', 'N}#DB<X0t!J)=y=m/6VWi!W]HAYs$+W::dkrG{LhR9.Ow%FCify9:& q}t#4T+?K' );
define( 'WP_CACHE_KEY_SALT', '$*M-T-7)[zqPIa/B ;^+<<HR/mjK]Xdsto4bx@2{p3FhI&kh3(pK+Udih_wLX]RD' );

/**
 * WordPress Database Table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 */
$table_prefix = 'wp_';

// Enable WP_DEBUG mode
define( 'WP_DEBUG', true );

// Enable Debug logging to the /wp-content/debug.log file
define( 'WP_DEBUG_LOG', true );

// Disable display of errors and warnings
define( 'WP_DEBUG_DISPLAY', false );
@ini_set( 'display_errors', 0 );

// Use dev versions of core JS and CSS files (only needed if you are modifying these core files)
define( 'SCRIPT_DEBUG', true );


/* That's all, stop editing! Happy publishing. */
