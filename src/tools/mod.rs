//! Tools Module
//!
//! TigerStyle: Agent-facing tools for self-improvement and trajectory capture.

pub mod proposal;
pub mod trajectory;

pub use proposal::register_proposal_tool;
pub use trajectory::register_trajectory_tools;
