<?php

namespace App\Http\Requests;

use Illuminate\Contracts\Validation\ValidationRule;
use Illuminate\Foundation\Http\FormRequest;

class UpdateBookRequest extends FormRequest
{
    /**
     * Determine if the user is authorized to make this request.
     */
    public function authorize(): bool
    {
        return true;
    }

    /**
     * Get the validation rules that apply to the request.
     *
     * @return array<string, ValidationRule|array<mixed>|string>
     */
    public function rules(): array
    {
        return [
            //

             'title' => 'required|string|max:255',

            'author' => 'required|string|max:255',

            'category' => 'required|string|max:255',

            'publish_year' => 'required|integer|min:0|max:' . date('Y'),
        ];

    }

  public function messages(): array
    {
        return [

            'title.required' => 'Book title is required.',

            'author.required' => 'Author is required.',

            'category.required' => 'Category is required.',

            'publish_year.required' => 'Publish year is required.',

            'publish_year.max' => 'Publish year cannot be in the future.',

        ];
    }



}
