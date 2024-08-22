/* Project specific Javascript goes here. */

function add_asterisk(input) {
  var label = $(input).find('label:first').text();
  if (label.includes('*') == false) {
    label = label.trim() + '*';
    $(input).find('label:first').text(label);
  }
}

function check_medallergy(treatment) {
  // function that checks whether a medallergy checkbox is checked for a treatment
  // and shows the treatment_matype field if so
  var id = 'medallergy_' + treatment;
  if ($('#id_' + id).is(':checked')) {
    $('#div_id_' + treatment + '_matype').show();
  } else {
    $('#div_id_' + treatment + '_matype').hide();
    // uncheck the treatment_matype field
    $('#id_' + treatment + '_matype')
      .val('')
      .removeAttr('checked');
  }
}

function collapse_control() {
  // Function that toggles [show/hide] text of the button calling the function
  // Find the control for the collapse
  control = $('#' + $(this).attr('id') + '_control');
  // Change the control's text to show
  $(control).text('Show');
}

function datepickers() {
  $('.datepick').each(function () {
    $(this).datepicker({
      changeYear: true,
      minDate: '-2y',
      maxDate: '0',
    });
  });
}

function expand_control() {
  // Function that toggles [show/hide] text of the button calling the function
  // Find the control for the collapse
  control = $('#' + $(this).attr('id') + '_control');
  // Change the control's text to show
  $(control).text('Hide');
}

function remove_asterisk(input) {
  var label = $(input).find('label:first').text();
  if (label.includes('*') == true) {
    label.split('*');
    label = label;
    $(input).find('label:first').text(label);
  }
}

function update_minus(id) {
  // function that updates the plus/minus sign of the element with id=id
  var text = $('#' + id).text();
  if (!text.includes('(-)')) {
    var bool = $('#' + id).find('.collapse-bool');
    bool.html(function () {
      return '(-)';
    });
  }
}

function update_plus(id) {
  // function that updates the plus/minus sign of the element with id=id
  var text = $('#' + id).text();
  if (!text.includes('(+)')) {
    var bool = $('#' + id).find('.collapse-bool');
    bool.html(function () {
      return '(+)';
    });
  }
}

function get_id_in_hyperlink() {
  // function that checks for query parameters in the URL
  var url = window.location.href;
  // get url query parameter
  var query_parametrs = url.split('?');
  // get the related_object_id query parameter
  var last_url_segment = query_parametrs[query_parametrs.length - 1];
  // get the id from the last_url_segment
  var id = last_url_segment.split('#');
  return id[1];
}

function get_collapse_id_from_hyperlink_id(hyperlink_id) {
  // function that gets the collapse id from the hyperlink id
  //swap out - for _ in hyperlink_id
  var collapse_id = hyperlink_id.replace('-', '_');
  return collapse_id + '_collapse';
}

function check_if_id_collapse_hidden(id) {
  // function that checks if the collapse with id=id is hidden
  var collapse = $('#' + id);
  if (collapse.hasClass('show')) {
    return false;
  } else {
    return true;
  }
}

function expand_collapse_for_id_if_hidden() {
  hyperlink_id = get_id_in_hyperlink();
  console.log(hyperlink_id);
  // check if there is a hyperlink id
  if (hyperlink_id) {
    console.log('hyperlink_id found');
    // function that expands the collapse with id=id if it is hidden
    collapse_id = get_collapse_id_from_hyperlink_id(hyperlink_id);
    if (check_if_id_collapse_hidden(collapse_id)) {
      console.log('hidden');
      $('#' + collapse_id).collapse('show');
    }
  }
}

function check_for_and_expand_collapse() {
  // function that checks for query parameters in the URL
  var id = get_id_in_hyperlink();
  expand_collapse_for_id_if_hidden(id);
}

// function that checks whether or not CKD is checked and hides/shows dialysis/stage fields as appropriate
function CKD_checker(dob_optional, gender_optional, patient = false) {
  // function that checks whether CKD is checked or not, shows dialysis and stage fields or hides/empties them
  if ($('#id_CKD-value').find(':selected').val() == 'True') {
    $('#ckddetail').show();
    add_asterisk($('#dialysis'));
    dialysis_checker();
    var baselinecreatinine = $('#id_baselinecreatinine-value').val();
    if (
      baselinecreatinine != '' &&
      typeof baselinecreatinine != 'undefined' &&
      !patient
    ) {
      $('#dateofbirth').show();
      add_asterisk($('#dateofbirth'));
      $('#id_dateofbirth').prop('required', true);
      $('#gender').show();
      add_asterisk($('#gender'));
      $('#id_gender').prop('required', true);
    } else if (!patient) {
      if (dob_optional === 'True') {
        $('#dateofbirth').hide();
        remove_asterisk($('#dateofbirth'));
        $('#id_dateofbirth').prop('required', false);
      } else {
        $('#dateofbirth').show();
        add_asterisk($('#dateofbirth'));
        $('#id_dateofbirth').prop('required', true);
      }
      if (gender_optional === 'True') {
        $('#gender').hide();
        remove_asterisk($('#gender'));
        $('#id_gender').prop('required', false);
      } else {
        $('#gender').show();
        add_asterisk($('#gender'));
        $('#id_gender').prop('required', false);
      }
    }
  } else {
    $('#ckddetail').hide();
    remove_asterisk($('#dialysis'));
    dialysis_checker();
    if (!patient) {
      if (dob_optional === 'True') {
        $('#dateofbirth').hide();
        remove_asterisk($('#dateofbirth'));
        $('#id_dateofbirth').prop('required', false);
      } else {
        $('#dateofbirth').show();
        add_asterisk($('#dateofbirth'));
        $('#id_dateofbirth').prop('required', true);
      }
      if (gender_optional === 'True') {
        $('#gender').hide();
        remove_asterisk($('#gender'));
        $('#id_gender').prop('required', false);
      } else {
        $('#gender').show();
        add_asterisk($('#gender'));
        $('#id_gender').prop('required', false);
      }
    }
  }
}

// function that checks whether an OPTIONAL CKD is checked and hides/shows dateofbirth and gender fields as appropriate
function CKD_optional_checker(dob_optional, gender_optional, patient = false) {
  // function that checks whether CKD is checked or not, shows/hides dateofbirth and gender forms
  var baselinecreatinine = $('#id_baselinecreatinine-value').val();
  // Check if there's a baseline creatinine to show/hide dateofbirth and gender forms
  if (
    $('#id_CKD-value').find(':selected').val() == 'True' &&
    baselinecreatinine.length > 0 &&
    !patient
  ) {
    $('#dateofbirth').show();
    add_asterisk($('#dateofbirth'));
    $('#id_dateofbirth').prop('required', true);
    $('#gender').show();
    add_asterisk($('#gender'));
    $('#id_gender').prop('required', true);
  } else if (!patient) {
    if (dob_optional === 'True') {
      $('#dateofbirth').hide();
      remove_asterisk($('#dateofbirth'));
      $('#id_dateofbirth').prop('required', false);
    }
    if (gender_optional === 'True') {
      $('#gender').hide();
      remove_asterisk($('#gender'));
      $('#id_gender').prop('required', false);
    }
  }
}

// Method that removes a UrateForm from the formset
function removeUrate(id) {
  // remove the form with id=id
  var total = $('#id_urate-TOTAL_FORMS').val();
  var form = $('#' + id);
  if (total > 1) {
    form.remove();
    total--;
    $('#id_urate-TOTAL_FORMS').val(total);
  }
  // update the formset
  var forms = $('.urate-form');
  for (var i = 0, formCount = forms.length; i < formCount; i++) {
    $(forms.get(i))
      .find(':input')
      .each(function () {
        updateElementIndex(this, i);
      });
  }
}

function egfr_calc(creatinine, age, gender) {
  var creatinine = parseFloat(creatinine);
  var age = parseInt(age);
  var gender = parseInt(gender);
  if (gender == 0) {
    var sex_modifier = 1.0;
    var alpha = -0.302;
    var kappa = 0.9;
  } else {
    var sex_modifier = 1.012;
    var alpha = -0.241;
    var kappa = 0.7;
  }
  var egfr =
    142 *
    Math.min(creatinine / kappa, 1.0) ** alpha *
    Math.max(creatinine / kappa, 1.0) ** -1.2 *
    0.9938 ** age *
    sex_modifier;
  return egfr;
}

function labs_stage_calculator(egfr) {
  var egfr = parseInt(egfr);
  if (egfr >= 90) {
    var stage = 1;
  } else if (egfr >= 60) {
    var stage = 2;
  } else if (egfr >= 30) {
    var stage = 3;
  } else if (egfr >= 15) {
    var stage = 4;
  } else {
    var stage = 5;
  }
  return stage;
}

function compare_stage_creat(patient = false, u_age = 0, u_gender = 0) {
  if (patient) {
    var age = u_age;
    var gender = u_gender;
  } else {
    var age = $('#id_dateofbirth-value').val();
    var gender = $('#id_gender-value').val();
  }
  var stage = $('#id_stage').val();
  var baselinecreatinine = $('#id_baselinecreatinine-value').val();
  if (baselinecreatinine != '' && typeof baselinecreatinine != 'undefined') {
    if (age == '' || gender == '') {
      baselinecreatinine_error = `<span id='baselinecreatinine_error' css_class='invalid-feedback'><strong>Age and gender are needed to correctly interpret a baseline creatinine.</strong></span>`;
      dateofbirth_error = `<span id='dateofbirth_error' css_class='invalid-feedback'><strong>Age is needed to correctly interpret a baseline creatinine.</strong></span>`;
      gender_error = `<span id='gender_error' css_class='invalid-feedback'><strong>Gender is needed to correctly interpret a baseline creatinine.</strong></span>`;
      if ($('#baselinecreatinine_error').length > 0) {
        $('#baselinecreatinine_error').replaceWith(baselinecreatinine_error);
        $('#baselinecreatinine_error').css('display', 'block');
        $('#baselinecreatinine_error').css('margin-top', '0.25rem');
        $('#baselinecreatinine_error').css('font-size', '0.875rem');
        $('#baselinecreatinine_error').css('background-color', 'yellow');
      } else {
        $('#id_baselinecreatinine-value').after(baselinecreatinine_error);
        $('#baselinecreatinine_error').css('display', 'block');
        $('#baselinecreatinine_error').css('margin-top', '0.25rem');
        $('#baselinecreatinine_error').css('font-size', '0.875rem');
        $('#baselinecreatinine_error').css('background-color', 'yellow');
      }
      if (age == '' && !patient) {
        if ($('#dateofbirth_error').length > 0) {
          $('#dateofbirth_error').replaceWith(dateofbirth_error);
          $('#dateofbirth_error').css('display', 'block');
          $('#dateofbirth_error').css('margin-top', '0.25rem');
          $('#dateofbirth_error').css('font-size', '0.875rem');
          $('#dateofbirth_error').css('background-color', 'yellow');
        } else {
          $('#id_dateofbirth-value').after(dateofbirth_error);
          $('#dateofbirth_error').css('display', 'block');
          $('#dateofbirth_error').css('margin-top', '0.25rem');
          $('#dateofbirth_error').css('font-size', '0.875rem');
          $('#dateofbirth_error').css('background-color', 'yellow');
        }
      } else if (!patient) {
        $('#dateofbirth_error').remove();
      }
      if (gender == '' && !patient) {
        if ($('#gender_error').length > 0) {
          $('#gender_error').replaceWith(gender_error);
          $('#gender_error').css('display', 'block');
          $('#gender_error').css('margin-top', '0.25rem');
          $('#gender_error').css('font-size', '0.875rem');
          $('#gender_error').css('background-color', 'yellow');
        } else {
          $('#id_gender-value').after(gender_error);
          $('#gender_error').css('display', 'block');
          $('#gender_error').css('margin-top', '0.25rem');
          $('#gender_error').css('font-size', '0.875rem');
          $('#gender_error').css('background-color', 'yellow');
        }
      } else if (!patient) {
        $('#gender_error').remove();
      }
    } else {
      if ($('#dateofbirth_error').length > 0 && !patient) {
        $('#dateofbirth_error').remove();
      }
      if ($('#gender_error').length > 0 && !patient) {
        $('#gender_error').remove();
      }
      var egfr = egfr_calc(
        (creatinine = baselinecreatinine),
        (age = age),
        (gender = gender),
      );
      var stage_calc = labs_stage_calculator((egfr = egfr));
      if (stage.length & (stage_calc != stage)) {
        var stage_error = `<span id='stage_error' css_class='invalid-feedback'><strong>The stage (${stage}) selected does not match the calculated stage (${stage_calc}) from the baseline creatinine, age, and gender.</strong></span>`;
        var baselinecreatinine_error = `<span id='baselinecreatinine_error' css_class='invalid-feedback'><strong>The stage (${stage_calc}) calculated from the baseline creatinine, age, and gender does not match the select stage (${stage}).</strong></span>`;
        if ($('#stage_error').length > 0) {
          $('#stage_error').replaceWith(stage_error);
          $('#stage_error').css('display', 'block');
          $('#stage_error').css('margin-top', '0.25rem');
          $('#stage_error').css('font-size', '0.875rem');
          $('#stage_error').css('background-color', 'yellow');
        } else {
          $('#id_stage').after(stage_error);
          $('#stage_error').css('display', 'block');
          $('#stage_error').css('margin-top', '0.25rem');
          $('#stage_error').css('font-size', '0.875rem');
          $('#stage_error').css('background-color', 'yellow');
        }
        if ($('#baselinecreatinine_error').length > 0) {
          $('#baselinecreatinine_error').replaceWith(baselinecreatinine_error);
          $('#baselinecreatinine_error').css('display', 'block');
          $('#baselinecreatinine_error').css('margin-top', '0.25rem');
          $('#baselinecreatinine_error').css('font-size', '0.875rem');
          $('#baselinecreatinine_error').css('background-color', 'yellow');
        } else {
          $('#id_baselinecreatinine-value').after(baselinecreatinine_error);
          $('#baselinecreatinine_error').css('display', 'block');
          $('#baselinecreatinine_error').css('margin-top', '0.25rem');
          $('#baselinecreatinine_error').css('font-size', '0.875rem');
          $('#baselinecreatinine_error').css('background-color', 'yellow');
        }
      } else {
        if ($('#stage_error').length > 0) {
          $('#stage_error').remove();
        }
        if ($('#baselinecreatinine_error').length > 0) {
          $('#baselinecreatinine_error').remove();
        }
        if ($('#dateofbirth_error').length > 0 && !patient) {
          $('#dateofbirth_error').remove();
        }
        if ($('#gender_error').length > 0 && !patient) {
          $('#gender_error').remove();
        }
      }
    }
  } else {
    if ($('#stage_error').length > 0) {
      $('#stage_error').remove();
    }
    if ($('#baselinecreatinine_error').length > 0) {
      $('#baselinecreatinine_error').remove();
    }
    if ($('#dateofbirth_error').length > 0 && !patient) {
      $('#dateofbirth_error').remove();
    }
    if ($('#gender_error').length > 0 && !patient) {
      $('#gender_error').remove();
    }
  }
}

function dialysis_checker() {
  if ($('#id_dialysis').find(':selected').val() == 'True') {
    $('#dialysis').show();
    $('#dialysis_type').show();
    $('#id_dialysis_type').prop('required', true);
    add_asterisk($('#dialysis_type'));
    $('#dialysis_duration').show();
    $('#id_dialysis_duration').prop('required', true);
    add_asterisk($('#dialysis_duration'));
    $('#stage').hide();
    $('#id_stage').val('');
    $('#baselinecreatinine').hide();
    $('#id_baselinecreatinine-value').val('');
  } else if ($('#id_CKD-value').find(':selected').val() == 'True') {
    $('#dialysis_type').hide();
    $('#id_dialysis_type').val('');
    $('#id_dialysis_type').prop('required', false);
    remove_asterisk($('#dialysis_type'));
    $('#dialysis_duration').hide();
    $('#id_dialysis_duration').val('');
    $('#id_dialysis_duration').prop('required', false);
    remove_asterisk($('#dialysis_duration'));
    $('#stage').show();
    $('#baselinecreatinine').show();
  } else {
    $('#dialysis_type').hide();
    $('#id_dialysis_type').val('');
    $('#id_dialysis_type').prop('required', false);
    remove_asterisk($('#dialysis_type'));
    $('#dialysis_duration').hide();
    $('#id_dialysis_duration').val('');
    $('#id_dialysis_duration').prop('required', false);
    remove_asterisk($('#dialysis_duration'));
    $('#stage').hide();
    $('#id_stage').val('');
    $('#baselinecreatinine').hide();
    $('#id_baselinecreatinine-value').val('');
  }
}

// Flare JS
function flare_aki_checker() {
  // checks if aki is checked and shows/hides the aki sub-form fields
  // and removes the creatinines if aki is not checked
  if ($('#id_aki-value').val() == 'True') {
    $('#div_id_aki-status').show();
    $('#div_id_aki-status').prop('required', true);
    add_asterisk($('#div_id_aki-status'));
    $('#creatinines').show();
  } else {
    $('#div_id_aki-status').hide();
    $('#div_id_aki-status').prop('required', false);
    remove_asterisk($('#div_id_aki-status'));
    $('#creatinines').hide();
    creatinines_remove();
  }
}
function creatinines_remove() {
  // method that removes all creatinine forms from the formset
  var total = $('#id_creatinine-TOTAL_FORMS').val();
  // get all the non-empty-form dynamic forms in the creatinines div
  creatinine_forms = $('#creatinines').find('.dynamic-form').not('.empty-form');
  non_empty_forms = creatinine_forms.filter(function () {
    return $(this).find('input[id*="-value"]').val() != '';
  });
  for (var i = 0, formCount = non_empty_forms.length; i < formCount; i++) {
    // get the first id in any of it's children
    var id = $(non_empty_forms.get(i)).find(':input').first().attr('id');
    // Find the first element in the form div that has -DELETE in the id
    var delete_element = $(non_empty_forms.get(i))
      .find('[id*="-DELETE"]')
      .first();
    console.log(delete_element);
    // Get the anchor tag element from the delete_element
    var delete_input = $(delete_element).find('.formset-delete');
    console.log(delete_input);
    delete_input.click();
  }
}

function getAge(dateString) {
  var today = new Date();
  var birthDate = new Date(dateString);
  var age = today.getFullYear() - birthDate.getFullYear();
  var m = today.getMonth() - birthDate.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
    age--;
  }
  return age;
}

function menopause_checker(
  patient = false,
  change = false,
  u_age = 0,
  u_gender = 0,
) {
  if (patient) {
    var age = u_age;
    var gender = u_gender;
  } else {
    var age = $('#id_dateofbirth-value').val();
    var gender = $('#id_gender-value').val();
  }
  if (gender && gender == 1) {
    if (age && age >= 40 && age && age < 60) {
      $('#menopause').show();
      $('#id_MENOPAUSE-value').prop('required', true);
      add_asterisk($('#menopause'));
      if (change) {
        $('#id_MENOPAUSE-value').val('');
      }
    } else {
      remove_asterisk($('#menopause'));
      $('#id_MENOPAUSE-value').prop('required', false);
      $('#menopause').hide();
    }
  } else {
    remove_asterisk($('#menopause'));
    $('#id_MENOPAUSE-value').prop('required', false);
    $('#menopause').hide();
  }
}

function urate_checker() {
  if ($('#id_urate_check').val() == 'True') {
    $('#urate').show();
    add_asterisk($('#urate'));
  } else {
    $('#urate').hide();
    $('#id_urate-value').val('');
    remove_asterisk($('#urate'));
  }
}

function flare_aki_date_ended() {
  // method that checks if the date_ended field is blank and adjusts the
  // first word of the aki help_text to "Does" if it is blank and "Did" if it is not
  if ($('#id_date_ended').val() == '') {
    // change the first word of the help_text to "Does"
    var help_text = $('#hint_id_aki').text();
    intro = help_text.replace(/ .*/, '');
    if (intro != 'Does') {
      $('#hint_id_aki').text(help_text.replace(/[^\s]*/, 'Does'));
    }
  } else {
    // change the first word of the help_text to "Did"
    var help_text = $('#hint_id_aki').text();
    intro = help_text.replace(/ .*/, '');
    if (intro != 'Did') {
      $('#hint_id_aki').text(help_text.replace(/[^\s]*/, 'Did'));
    }
  }
}

function aki_show_subform() {
  // method that shows the aki subform if the aki field is True
  if ($('#id_aki_value').val() == 'True') {
    $('#div_id_aki_resolved').show();
    $('#div_id_aki_resolved').prop('required', true);
    add_asterisk($('#div_id_aki_resolved'));
    $('#creatinines').show();
  } else {
    $('#div_id_aki_resolved').hide();
    $('#div_id_aki_resolved').prop('required', false);
    remove_asterisk($('#div_id_aki_resolved'));
    $('#creatinines').hide();
  }
}
function aspiration_checker() {
  if ($('#id_aspiration').val() == 'True') {
    $('#crystal_analysis').show();
    $('#id_crystal_analysis').prop('required', true);
    add_asterisk($('#crystal_analysis'));
  } else {
    $('#crystal_analysis').hide();
    $('#id_crystal_analysis').val('');
    $('#id_crystal_analysis').prop('required', false);
    remove_asterisk($('#crystal_analysis'));
  }
}

function medical_evaluation_checker() {
  if ($('#id_medical_evaluation').val() == 'True') {
    $('#aki').show();
    $('#div_id_aki').prop('required', true);
    add_asterisk($('#div_id_aki'));
    $('#urate-sub-form').show();
    $('#div_id_urate_check').prop('required', true);
    add_asterisk($('#div_id_urate_check'));
    urate_checker();
    $('#diagnosed').show();
    $('#div_id_diagnosed').prop('required', true);
    add_asterisk($('#div_id_diagnosed'));
    $('#aspiration-sub-form').show();
    $('#div_id_aspiration').prop('required', true);
    add_asterisk($('#div_id_aspiration'));
    aspiration_checker();
  } else {
    $('#aki').hide();
    $('#div_id_aki').prop('required', false);
    $('#id_aki').val('');
    remove_asterisk($('#div_id_aki'));
    $('#urate-sub-form').hide();
    $('#div_id_urate_check').prop('required', false);
    $('#id_urate_check').val('');
    remove_asterisk($('#div_id_urate_check'));
    urate_checker();
    $('#diagnosed').hide();
    $('#div_id_diagnosed').prop('required', false);
    $('#id_diagnosed').val('');
    remove_asterisk($('#div_id_diagnosed'));
    $('#aspiration-sub-form').hide();
    $('#div_id_aspiration').prop('required', false);
    $('#id_aspiration').val('');
    remove_asterisk($('#div_id_aspiration'));
    aspiration_checker();
  }
}

// Contact js
// Method that checks the value of the subject field and
// shows/hides and adds/removes required from the other field
function subject_checker() {
  // Check if the subject is 'other'
  if ($('#id_subject').val() == 'other') {
    // If so, make the other field required and show it
    $('#div_id_other').show();
    $('#id_other').prop('required', true);
    add_asterisk($('#div_id_other'));
    // If not, make the other field not required and hide it
  } else {
    $('#div_id_other').hide();
    $('#id_other').prop('required', false);
    remove_asterisk($('#div_id_other'));
    // Set the id_other val to null
    $('#id_other').val('');
  }
}

// Ppx JS
function at_goal_checker() {
  // function that checks whether the at_goal field is True and shows/hides the at_goal_long_term field
  if ($('#id_at_goal').val() == 'True') {
    $('#at_goal_long_term').show();
  } else {
    $('#at_goal_long_term').hide();
    $('#id_at_goal_long_term').prop('value', 'False');
  }
}

function starting_ult_checker(subject_the, Tobe, pos, gender_subject) {
  // function that updates the help text of the starting_ult field
  // first get the on_ult field value
  var on_ult = $('#id_on_ult').val();
  // then check if on_ult is true
  if (on_ult == 'True') {
    $('#div_id_starting_ult').show();
    $('#starting_ult_help_text_extra').hide();
    // if on_Ult is true, change help text to "Has the patient started
    // ULT in the last 3 months?"
    $('#starting_ult_help_text').text(
      `${Tobe} ${subject_the} in the initial dose-adjustment phase (e.g. titration, usually first 6-12 months) of urate-lowering therapy (ULT)?`,
    );
  } else if (on_ult == 'False') {
    $('#div_id_starting_ult').show();
    $('#starting_ult_help_text_extra').show();
    // if on_ult is false or null, change help_text to "Is the patient starting ULT ("urate-lowering therapy")?"
    $('#starting_ult_help_text').text(
      `Is ${subject_the} just starting ULT (urate-lowering therapy) or ${pos} ${gender_subject} started ULT in the last 3 months?`,
    );
  } else {
    // hide the starting_ult field
    $('#div_id_starting_ult').hide();
  }
}

// Ult JS
function ult_checker() {
  if ($('#id_num_flares').val() != 2) {
    $('#id_freq_flares').val('');
    remove_asterisk($('#freq_flares'));
    $('#id_freq_flares').prop('required', false);
    $('#freq_flares').hide();
  } else {
    $('#freq_flares').show();
    $('#id_freq_flares').prop('required', true);
    add_asterisk($('#freq_flares'));
  }
}
