<?php
namespace PMStats;

/**
 * Stats class
 *
 * Extract stats
 *
 *
 * @package PMStats
 */
class Stats
{
    /**
     * Get a list of files, based on the extension
     *
     * @param string $path      Path to folder to analyze
     * @param string $extension Extension to search for
     *
     * @return array List of file names
     */
    private static function getDirContents($path, $extension)
    {
        $rii = new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator($path));
        $files = [];
        foreach ($rii as $file) {
            if (! $file->isDir()) {
                $ext = pathinfo($file, PATHINFO_EXTENSION);
                if ($ext == 'lang') {
                    $files[] = $file->getPathname();
                }
            }
        }

        return $files;
    }

    /**
     * Get word count
     *
     * @param string $text Text to check
     *
     * @return integer Word count
     */
    private static function getWordCount($text)
    {
        return str_word_count(strip_tags($text));
    }

    /**
     * Get stats per file
     *
     * @param string $path       Path to files
     * @param array  $changesets Array of changesets
     * @param string $format     Format to analyze
     *
     * @return array Stats
     */
    public static function getStats($path, $changesets, $format)
    {
        $previous_cache = [];
        $stats = [];
        foreach ($changesets as $day => $changeset) {
            exec("git checkout {$changeset}");

            # Initialize stats
            $stats[$day] = [
                'added'     => 0,
                'added_w'   => 0,
                'removed'   => 0,
                'removed_w' => 0,
                'total'     => 0,
                'total_w'   => 0,
            ];
            $file_list = self::getDirContents($path, 'lang');

            # Create cache of strings
            $cache = [];
            foreach ($file_list as $current_filename) {
                switch ($format) {
                    case 'lang':
                        $file_content = DotLangParser::parseFile($current_filename);
                        break;
                    default:
                        break;
                }
                foreach ($file_content['strings'] as $string_id => $string_value) {
                    switch ($format) {
                        case 'lang':
                            $id = $current_filename . ':' . hash('md5', $string_id);
                            break;
                        default:
                            break;
                    }
                    $cache[$id] = $string_value;
                }
                $stats[$day]['total'] += count($file_content['strings']);
                $stats[$day]['total_w'] += array_sum(array_map('self::getWordCount', $file_content['strings']));
            }

            # First run, there are no added or remove
            if (empty($previous_cache)) {
                $previous_cache = $cache;
                continue;
            }

            # Count removed strings
            $removed_strings = array_diff_key($previous_cache, $cache);
            foreach ($removed_strings as $string_id => $text) {
                $stats[$day]['removed_w'] += self::getWordCount($text);
            }
            $stats[$day]['removed'] += count($removed_strings);

            # Count added strings
            $added_strings = array_diff_key($cache, $previous_cache);
            foreach ($added_strings as $string_id => $text) {
                $stats[$day]['added_w'] += self::getWordCount($text);
            }
            $stats[$day]['added'] += count($added_strings);

            # Store current cache as previous cache and move on
            $previous_cache = $cache;
        }

        return $stats;
    }


    /**
     * Get overall stats per year
     *
     * @param array $stat Array of stats
     *
     * @return array Stats
     */
    public static function getGeneralStats($stats)
    {
        $overall_stats = [];
        foreach ($stats as $day => $data) {
            $year = substr($day, 0, 4);
            if (! isset($overall_stats[$year])) {
                $overall_stats[$year] = [
                    'added'     => 0,
                    'added_w'   => 0,
                    'removed'   => 0,
                    'removed_w' => 0,
                    'total'     => 0,
                    'total_w'   => 0,
                ];
            } else {
                $overall_stats[$year]['added'] += $data['added'];
                $overall_stats[$year]['added_w'] += $data['added_w'];
                $overall_stats[$year]['removed'] += $data['removed'];
                $overall_stats[$year]['removed_w'] += $data['removed_w'];
                $overall_stats[$year]['total'] = $data['total'];
                $overall_stats[$year]['total_w'] = $data['total_w'];
            }
        }

        return $overall_stats;
    }
}
