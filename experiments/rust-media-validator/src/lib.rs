use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[pyfunction]
#[pyo3(signature = (data, is_map=false))]
fn validate_media(data: &[u8], is_map: bool) -> PyResult<()> {
    check_media(data, is_map).map_err(PyValueError::new_err)
}

fn check_media(data: &[u8], is_map: bool) -> Result<(), &'static str> {
    if data.is_empty() {
        return Err("Empty media response");
    }
    if data[0] == 0x47 && !is_map {
        if data.len() % 188 != 0 || data.iter().step_by(188).any(|byte| *byte != 0x47) {
            return Err("Incomplete transport stream");
        }
        return Ok(());
    }
    let mut offset = 0;
    let (mut moov, mut moof, mut mdat) = (false, false, false);
    while offset < data.len() {
        if data.len() - offset < 8 {
            return Err("Incomplete MP4 box header");
        }
        let mut size = u32::from_be_bytes(data[offset..offset + 4].try_into().unwrap()) as u64;
        let mut header = 8;
        if size == 1 {
            if data.len() - offset < 16 {
                return Err("Incomplete MP4 extended size");
            }
            size = u64::from_be_bytes(data[offset + 8..offset + 16].try_into().unwrap());
            header = 16;
        } else if size == 0 {
            size = (data.len() - offset) as u64;
        }
        if size < header || size > (data.len() - offset) as u64 {
            return Err("Incomplete MP4 box");
        }
        match &data[offset + 4..offset + 8] {
            b"moov" => moov = true,
            b"moof" => moof = true,
            b"mdat" => mdat = true,
            _ => {}
        }
        offset += size as usize;
    }
    if (is_map && !moov) || (!is_map && !(moof && mdat)) {
        return Err("Unexpected media container");
    }
    Ok(())
}

#[pymodule]
fn rust_media_validator(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(validate_media, module)?)
}
