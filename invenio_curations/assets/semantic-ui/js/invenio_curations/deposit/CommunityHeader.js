// This file is part of Invenio-RDM-Records
// Copyright (C) 2020-2024 CERN.
// Copyright (C) 2020-2022 Northwestern University.
// Copyright (C) 2021-2022 Graz University of Technology.
//
// Invenio-RDM-Records is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import { i18next } from "@translations/invenio_rdm_records/i18next";
import PropTypes from "prop-types";
import React, { Component } from "react";
import { Image } from "react-invenio-forms";
import { connect } from "react-redux";
import { Button, Container } from "semantic-ui-react";
import { changeSelectedCommunity } from "@js/invenio_rdm_records/src/deposit/state/actions";
import { CommunitySelectionModal } from "@js/invenio_rdm_records/src/deposit/components/CommunitySelectionModal";

class CommunityHeaderComponent extends Component {
  constructor(props) {
    super(props);
    this.state = {
      modalOpen: false,
    };
  }

  render() {
    const {
      changeSelectedCommunity,
      community,
      imagePlaceholderLink,
      showCommunitySelectionButton,
      disableCommunitySelectionButton,
      userCanManageRecord,
      record,
      showCommunityHeader,
    } = this.props;
    const { modalOpen } = this.state;

    // record is coming from the Jinja template and it is refreshed on page reload
    const isNewUpload = !record.id;
    // Check if the user can manage the record only if it is not a new upload
    const isCommunitySelectionDisabled =
      (!isNewUpload && !userCanManageRecord) || disableCommunitySelectionButton;

    return (
          <>
            <CommunitySelectionModal
              onCommunityChange={(community) => {
                changeSelectedCommunity(community);
                this.setState({ modalOpen: false });
              }}
              onModalChange={(value) => this.setState({ modalOpen: value })}
              modalOpen={modalOpen}
              chosenCommunity={community}
              displaySelected
              record={record}
              trigger={
                  <Button
                    className="community-header-button"
                    disabled={isCommunitySelectionDisabled}
                    onClick={() => this.setState({ modalOpen: true })}
                    primary
                    size="mini"
                    name="setting"
                    type="button"
                    content={
                      community
                        ? i18next.t("Change")
                        : i18next.t("Select a community")
                    }
                  />
              }
            />
              {community && (
                <Button
                  basic
                  id="remove-community-button"
                  size="mini"
                  labelPosition="left"
                  className="community-header-button ml-5"
                  onClick={() => changeSelectedCommunity(null)}
                  content={i18next.t("Remove")}
                  icon="close"
                  disabled={isCommunitySelectionDisabled}
                />
              )}
          </>
      )
  }
}

CommunityHeaderComponent.propTypes = {
  imagePlaceholderLink: PropTypes.string.isRequired,
  community: PropTypes.object,
  disableCommunitySelectionButton: PropTypes.bool.isRequired,
  showCommunitySelectionButton: PropTypes.bool.isRequired,
  showCommunityHeader: PropTypes.bool.isRequired,
  changeSelectedCommunity: PropTypes.func.isRequired,
  record: PropTypes.object.isRequired,
  userCanManageRecord: PropTypes.bool.isRequired,
};

CommunityHeaderComponent.defaultProps = {
  community: undefined,
};

const mapStateToProps = (state) => ({
  community: state.deposit.editorState.selectedCommunity,
  disableCommunitySelectionButton:
    state.deposit.editorState.ui.disableCommunitySelectionButton,
  showCommunitySelectionButton:
    state.deposit.editorState.ui.showCommunitySelectionButton,
  showCommunityHeader: state.deposit.editorState.ui.showCommunityHeader,
  userCanManageRecord: state.deposit.permissions.can_manage,
  record: state.deposit.record,
});

const mapDispatchToProps = (dispatch) => ({
  changeSelectedCommunity: (community) => dispatch(changeSelectedCommunity(community)),
});

export const CommunityHeader = connect(
  mapStateToProps,
  mapDispatchToProps
)(CommunityHeaderComponent);
