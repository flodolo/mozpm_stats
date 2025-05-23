<?php
namespace PMStats;

use Gettext\Translations;

/**
 * Po class
 *
 * This class is used to manipulate translation files in Gettext (.po) format.
 *
 * @package PMStats
 */
class Po
{
    /**
     *
     * Loads strings from a .po file
     *
     * @param string  $po_path  Path to the .po to load
     * @param boolean $template If I'm looking at templates
     *
     * @return array Array of strings as [string_id => translation]
     */
    public static function getStrings($po_path, $template = false)
    {
        $translations = Translations::fromPoFile($po_path);
        $strings = [];

        $file_name = basename($po_path);

        foreach ($translations as $translation_obj) {
            $translated_string = $translation_obj->getTranslation();

            // Ignore fuzzy strings
            if (in_array('fuzzy', $translation_obj->getFlags())) {
                continue;
            }

            // Ignore empty (untranslated) strings
            if ($translated_string == '' && ! $template) {
                continue;
            }

            // In templates, use the original string as translation
            if ($template) {
                $translated_string = $translation_obj->getOriginal();
            }

            $string_id = self::generateStringID(
                $file_name,
                $translation_obj->getContext() . '-' . $translation_obj->getOriginal()
            );
            $translated_string = str_replace("'", "\\'", $translated_string);
            $strings[$string_id] = $translated_string;

            // Check if there are plurals, in case put them as translation of
            // the only English plural form
            if ($translation_obj->hasPluralTranslations()) {
                $string_id = self::generateStringID(
                    $file_name,
                    $translation_obj->getContext() . '-' . $translation_obj->getPlural()
                );
                $translated_string = implode("\n", $translation_obj->getPluralTranslations());
                $translated_string = str_replace("'", "\\'", $translated_string);
                $strings[$string_id] = $translated_string;
            }
        }

        return $strings;
    }

    /**
     * Generate a unique ID for a string to store in Transvision.
     *
     * @param string $file_name .po file name
     * @param string $string_id String ID (context-original text)
     *
     * @return string unique ID such as focus_android/app.po:1dafea7725862ca854c408f0e2df9c88
     */
    public static function generateStringID($file_name, $string_id)
    {
        return "{$file_name}:" . hash('md5', $string_id);
    }
}
