<?php
namespace PMStats;

/**
 * Utils class
 *
 * Utility functions like string management.
 *
 *
 * @package PMStats
 */
class Utils
{
    /**
     * Read CLI parameter if set, or fallback
     *
     * @param integer $paramnum Argument number
     * @param array   $options  Array of parameters
     * @param string  $fallback Optional fallback value
     *
     * @return string Parameter value, or fallback
     */
    public static function getCliParam($paramnum, $options, $fallback = '')
    {
        if (isset($options[$paramnum])) {
            return self::secureText($options[$paramnum]);
        }

        return $fallback;
    }

    /**
     * Function sanitizing a string or an array of strings.
     *
     * @param mixed   $origin  String/Array of strings to sanitize
     * @param boolean $isarray If $origin must be treated as array
     *
     * @return mixed Sanitized string or array
     */
    public static function secureText($origin, $isarray = true)
    {
        if (! is_array($origin)) {
            // If $origin is a string, always return a string
            $origin = [$origin];
            $isarray = false;
        }

        foreach ($origin as $item => $value) {
            // CRLF XSS
            $item = str_replace('%0D', '', $item);
            $item = str_replace('%0A', '', $item);
            $value = str_replace('%0D', '', $value);
            $value = str_replace('%0A', '', $value);

            $value = filter_var(
                $value,
                FILTER_SANITIZE_STRING,
                FILTER_FLAG_STRIP_LOW
            );

            $item = htmlspecialchars(strip_tags($item), ENT_QUOTES);
            $value = htmlspecialchars(strip_tags($value), ENT_QUOTES);

            // Repopulate value
            $sanitized[$item] = $value;
        }

        return ($isarray == true) ? $sanitized : $sanitized[0];
    }

    /**
     * Check if $haystack starts with a string in $needles.
     * $needles can be a string or an array of strings.
     *
     * @param string $haystack String to analyse
     * @param array  $needles  The strings to look for
     *
     * @return boolean True       if the $haystack string starts with a
     *                 string in $needles
     */
    public static function startsWith($haystack, $needles)
    {
        // Lang file common case: reference string
        if ($needles === ';') {
            return $haystack[0] == ';';
        }

        // Lang file common case: comment
        if ($needles === '#') {
            return $haystack[0] == '#';
        }

        foreach ((array) $needles as $needle) {
            if (mb_strpos($haystack, $needle, 0) === 0) {
                return true;
            }
        }

        return false;
    }

    /**
     * Remove a substring from the left of a string, return the trimmed result
     *
     * @param string $origin    Original string
     * @param string $substring Substring to remove
     *
     * @return string Resulting string
     */
    public static function leftStrip($origin, $substring)
    {
        // Lang file common cases: reference string or comment
        if ($substring === ';' || $substring === '#') {
            return trim(mb_substr($origin, 1));
        }

        return trim(mb_substr($origin, mb_strlen($substring)));
    }
}
