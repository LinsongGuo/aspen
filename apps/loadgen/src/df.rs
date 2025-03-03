use Packet;

use byteorder::{LittleEndian, ReadBytesExt, WriteBytesExt};
use clap::Arg;
use std::io;
use std::io::Read;

pub enum DFReqType {
    Req1 = 0x1,
    Req2 = 0x2,
    Req3 = 0x3,
    Req4 = 0x4,
    Req5 = 0x5
}

struct DFHeader {
    id: u32,
    req_type: u32,
    req_size: u32,
    run_ns: u32,
}

const HEADER_SIZE: usize = 16;

use Connection;
use LoadgenProtocol;
use Transport;

#[derive(Clone, Copy)]
pub struct DFProtocol {
    nvalues: u64,
    pct1: u64,
    pct2: u64,
    pct3: u64,
    pct4: u64,
}

impl LoadgenProtocol for DFProtocol {
    fn gen_req(&self, i: usize, p: &Packet, buf: &mut Vec<u8>) -> u64 {
        // Use first 32 bits of randomness to determine if this is a GET or SCAN req
        let low32 = p.randomness & 0xffffffff;
        let key = (p.randomness >> 32) % self.nvalues;
        let mut req_type = DFReqType::Req5;

        if low32 % 1000 < self.pct1 {
            req_type = DFReqType::Req1;
        } else if low32 % 1000 < self.pct2 {
            req_type = DFReqType::Req2;
        } else if low32 % 1000 < self.pct3 {
            req_type = DFReqType::Req3;
        } else if low32 % 1000 < self.pct4 {
            req_type = DFReqType::Req4;
        }

        let rtype = req_type as u64;
        // println!("req_type: {}", rtype);
        
        DFHeader {
            id: i as u32,
            req_type: rtype as u32,
            req_size: key as u32,
            run_ns: 0,
        }
        .serialize_into(buf)
        .unwrap();

        return rtype;
    }

    fn read_response(&self, mut sock: &Connection, scratch: &mut [u8]) -> io::Result<(usize, u64)> {
        sock.read_exact(&mut scratch[..HEADER_SIZE])?;
        let header = DFHeader::deserialize(&mut &scratch[..])?;
        Ok((header.id as usize, header.req_type as u64))
    }

    fn read_response_w_server_lat(&self, mut sock: &Connection, scratch: &mut [u8]) -> io::Result<(usize, u64, u64)> {
        sock.read_exact(&mut scratch[..HEADER_SIZE])?;
        let header = DFHeader::deserialize(&mut &scratch[..])?;
        Ok((header.id as usize, header.req_type as u64, (header.run_ns/2100) as u64))
    }
}

impl DFProtocol {
    pub fn with_args(matches: &clap::ArgMatches, tport: Transport) -> Self {
        if let Transport::Tcp = tport {
            panic!("tcp is unsupported by the DF protocol");
        }

        DFProtocol {
            nvalues: 1, // value_t!(matches, "r_nvalues", u64).unwrap(),
            pct1: 200, // value_t!(matches, "pctscan", u64).unwrap(),
            pct2: 400,
            pct3: 600,
            pct4: 800,
        }

        // DFProtocol {
        //     nvalues: 1, // value_t!(matches, "r_nvalues", u64).unwrap(),
        //     pct1: 0, // value_t!(matches, "pctscan", u64).unwrap(),
        //     pct2: 0,
        //     pct3: 1000,
        //     pct4: 0,
        // }
    }

    pub fn args<'a, 'b>() -> Vec<clap::Arg<'a, 'b>> {
        vec![
            Arg::with_name("r_nvalues")
        .long("r_nvalues")
        .takes_value(true)
        .default_value("1")
        .help("DF: number of key value pairs"),
            Arg::with_name("pctscan")
		.long("pct1")
		.takes_value(true)
		.default_value("0")
		.help("DF: req1 requests per 1000 requests"),
	]
    }
}

impl DFHeader {
    pub fn serialize_into<W: io::Write>(&self, writer: &mut W) -> io::Result<()> {
        writer.write_u32::<LittleEndian>(self.id)?;
        writer.write_u32::<LittleEndian>(self.req_type)?;
        writer.write_u32::<LittleEndian>(self.req_size)?;
        writer.write_u32::<LittleEndian>(self.run_ns)?;
        Ok(())
    }

    pub fn deserialize<R: io::Read>(reader: &mut R) -> io::Result<DFHeader> {
        let p = DFHeader {
            id: reader.read_u32::<LittleEndian>()?,
            req_type: reader.read_u32::<LittleEndian>()?,
            req_size: reader.read_u32::<LittleEndian>()?,
            run_ns: reader.read_u32::<LittleEndian>()?,
        };
        return Ok(p);
    }
}
