<?php

$config = new PhpCsFixer\Config();
$config
    ->setRiskyAllowed(true)
    ->setRules(
        [
            'array_syntax' => [
                'syntax' => 'short',
            ],
            'binary_operator_spaces' => [
                'operators' => [
                  '=>' => 'align',
                ],
            ],
            'blank_line_before_statement' => [
                'statements' => ['return']
            ],
            'cast_spaces'              => true,
            'concat_space'             => [
                'spacing' => 'one',
            ],
            'encoding'                           => true,
            'full_opening_tag'                   => true,
            'method_argument_space'            => [
                'on_multiline' => 'ignore',
                'keep_multiple_spaces_after_comma' => false,
            ],
            'no_alias_functions'                 => true,
            'no_blank_lines_after_class_opening' => true,
            'no_blank_lines_after_phpdoc'        => true,
            'no_empty_statement'                 => true,
            'no_extra_blank_lines'   => [
                'tokens' => [
                    'break', 'continue', 'extra', 'return', 'throw', 'use',
                    'parenthesis_brace_block', 'square_brace_block',
                    'curly_brace_block',
                ],
            ],
            'no_leading_import_slash'                    => true,
            'no_leading_namespace_whitespace'            => true,
            'no_singleline_whitespace_before_semicolons' => true,
            'no_trailing_comma_in_singleline'            => true,
            'no_unused_imports'                          => true,
            'no_whitespace_in_blank_line'                => true,
            'object_operator_without_whitespace'         => true,
            'ordered_imports'                            => true,
            'phpdoc_align'                               => true,
            'phpdoc_indent'                              => true,
            'phpdoc_separation'                          => true,
            'phpdoc_types'                               => true,
            'psr_autoloading'                            => true,
            'simplified_null_return'                     => true,
            'single_quote'                               => true,
            'standardize_not_equals'                     => true,
            'ternary_operator_spaces'                    => true,
            'trailing_comma_in_multiline'                => true,
            'trim_array_spaces'                          => true,
        ]
    )
    ->setFinder(
        PhpCsFixer\Finder::create()
            ->exclude('vendor')
            ->exclude('web/TMX')
            ->in(__DIR__)
    )
;

return $config;
