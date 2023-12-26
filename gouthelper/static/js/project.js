/* Project specific Javascript goes here. */

function add_asterisk(input) {
  var label = $(input).find('label:first').text();
  if (label.includes('*') == false) {
    label = label.trim() + '*';
    $(input).find('label:first').text(label);
  }
}

function check_plusminus(id) {
  // function that checks whether (+) or (-) is in the text of the element with id=id
  // and toggles collapse to open if (+) and close if (-)
  var text = $('#' + id).text();
  var explanation = '#' + id.split('-')[0] + '-explanation';
  if (text.includes('(+)')) {
    // check if explanation is collapsed
    if ($(explanation).is('.collapse:not(.show)') == true) {
      $(explanation).collapse('show');
    }
  } else {
    // check if explanation is expanded
    if ($(explanation).is('.collapse:not(.show)') == false) {
      $(explanation).collapse('hide');
    }
  }
}

function collapse_control() {
  // function that toggles [expand/collapse] text of element with id=id
  var toggle_id = '#' + $(this).attr('id').split('-')[0] + '-toggle';
  var control = $(toggle_id).find('.collapse-control');
  control
    .html(function () {
      return '<small><italic>[expand]</italic></small>';
    })
    .css('font-style', 'italic');
}

function expand_control() {
  // function that toggles [expand/collapse] text of element with id=id
  var toggle_id = '#' + $(this).attr('id').split('-')[0] + '-toggle';
  var control = $(toggle_id).find('.collapse-control');
  control
    .html(function () {
      return '<small>[collapse]</small>';
    })
    .css('font-style', 'italic');
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

// function that checks whether or not CKD is checked and hides/shows dialysis/stage fields as appropriate
function CKD_checker() {
  // function that checks whether CKD is checked or not, shows dialysis and stage fields or hides/empties them
  if ($('#id_CKD-value').find(':selected').val() == 'True') {
    $('#ckddetail').show();
    add_asterisk($('#dialysis'));
    dialysis_checker();
  } else {
    $('#ckddetail').hide();
    remove_asterisk($('#dialysis'));
    dialysis_checker();
  }
}

// function that checks whether an OPTIONAL CKD is checked and hides/shows dateofbirth and gender fields as appropriate
function CKD_optional_checker() {
  // function that checks whether CKD is checked or not, shows/hides dateofbirth and gender forms
  var baselinecreatinine = $('#id_baselinecreatinine-value').val();
  // Check if there's a baseline creatinine to show/hide dateofbirth and gender forms
  if (
    ($('#id_CKD-value').find(':selected').val() == 'True') &
    (baselinecreatinine.length > 0)
  ) {
    $('#dateofbirth').show();
    add_asterisk($('#dateofbirth'));
    $('#id_dateofbirth').prop('required', true);
    $('#gender').show();
    add_asterisk($('#gender'));
    $('#id_gender').prop('required', true);
  } else {
    $('#dateofbirth').hide();
    remove_asterisk($('#dateofbirth'));
    $('#id_dateofbirth').prop('required', false);
    $('#gender').hide();
    remove_asterisk($('#gender'));
    $('#id_gender').prop('required', false);
  }
}

// function that duplicates a Lab ModelForm and adds it to a formset
function cloneLab(selector, type) {
  var newElement = $(selector).clone(true);
  var total = $('#id_' + type + '-TOTAL_FORMS').val();
  newElement.find(':input').each(function () {
    var name = $(this)
      .attr('name')
      .replace('-' + (total - 1) + '-', '-' + total + '-');
    var id = 'id_' + name;
    // remove hasDatepicker class, required in order to refresh datepicker
    var css_class = $(this).attr('class');
    // check if css_class is not undefined and if it has 'hasDatepicker' in the class
    if (css_class !== undefined && css_class.includes('hasDatepicker')) {
      css_class = css_class.replace('hasDatepicker', '');
    }
    $(this).attr('class', css_class);
    $(this).attr({ name: name, id: id }).val('').removeAttr('checked');
  });
  newElement.find('label').each(function () {
    var newFor = $(this)
      .attr('for')
      .replace('-' + (total - 1) + '-', '-' + total + '-');
    $(this).attr('for', newFor);
  });
  total++;
  $('#id_' + type + '-TOTAL_FORMS').val(total);
  $(selector).after(newElement);
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

function compare_stage_creat() {
  var age = $('#id_dateofbirth-value').val();
  var gender = $('#id_gender-value').val();
  var creatinine = $('#id_baselinecreatinine-value').val();
  var stage = $('#id_stage').val();
  var baselinecreatinine = $('#id_baselinecreatinine-value').val();
  var stage = $('#id_stage').val();
  if (baselinecreatinine != '' && typeof baselinecreatinine != 'undefined') {
    if (isNaN(age) || gender == '') {
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
      if (isNaN(age)) {
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
      } else {
        $('#dateofbirth_error').remove();
      }
      if (gender == '') {
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
      } else {
        $('#gender_error').remove();
      }
    } else {
      if ($('#dateofbirth_error').length > 0) {
        $('#dateofbirth_error').remove();
      }
      if ($('#gender_error').length > 0) {
        $('#gender_error').remove();
      }
      var egfr = egfr_calc(
        (creatinine = creatinine),
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
        if ($('#dateofbirth_error').length > 0) {
          $('#dateofbirth_error').remove();
        }
        if ($('#gender_error').length > 0) {
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
    if ($('#dateofbirth_error').length > 0) {
      $('#dateofbirth_error').remove();
    }
    if ($('#gender_error').length > 0) {
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

function menopause_checker() {
  if ($('#id_gender-value').find(':selected').val() == 1) {
    var age = $('#id_dateofbirth-value').val();
    if (age >= 40 && age < 60) {
      $('#menopause').show();
      $('#id_MENOPAUSE-value').prop('required', true);
      add_asterisk($('#menopause'));
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
    $('#id_urate-value').prop('required', true);
    add_asterisk($('#urate'));
  } else {
    $('#urate').hide();
    $('#id_urate-value').val('');
    $('#id_urate-value').prop('required', false);
    remove_asterisk($('#urate'));
  }
}

function diagnosed_checker() {
  if ($('#id_diagnosed').val() == 'True') {
    $('#aspiration').show();
    $('#div_id_aspiration').prop('required', true);
    add_asterisk($('#div_id_aspiration'));
    if ($('#id_aspiration').val() == 'True') {
      $('#crystal_analysis').show();
      $('#div_id_crystal_analysis').val('required', true);
      add_asterisk($('#div_id_crystal_analysis'));
    } else {
      $('#crystal_analysis').hide();
      $('#div_id_crystal_analysis').prop('required', false);
      $('#id_crystal_analysis').val('');
      remove_asterisk($('#div_id_crystal_analysis'));
    }
  } else {
    $('#aspiration').hide();
    $('#div_id_aspiration').prop('required', false);
    $('#id_aspiration').val('');
    $('#crystal_analysis').hide();
    $('#div_id_crystal_analysis').prop('required', false);
    $('#id_crystal_analysis').val('');
    remove_asterisk($('#div_id_crystal_analysis'));
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
function starting_ult_help_text() {
  // function that updates the help text of the starting_ult field
  // first get the on_ult field value
  var on_ult = $('#id_on_ult').val();
  // then check if on_ult is true
  if (on_ult == 'True') {
    // if on_Ult is true, change help text to "Has the patient started
    // ULT in the last 3 months?"
    $('#hint_id_starting_ult').text(
      'Has the patient started ULT ("urate-lowering therapy") in the last 3 months?',
    );
  } else {
    // if on_ult is false or null, change help_text to "Is the patient starting ULT ("urate-lowering therapy")?"
    $('#hint_id_starting_ult').text(
      'Is the patient starting ULT ("urate-lowering therapy")?',
    );
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
